from kinfold_api.services.auth import (
    consume_login_state,
    create_login_state,
    find_or_create_owner_from_github,
    issue_login_key,
)


def test_same_github_id_reuses_the_same_owner(db_session):
    owner_a = find_or_create_owner_from_github(db_session, github_id="42", login="Octocat")
    owner_b = find_or_create_owner_from_github(db_session, github_id="42", login="Octocat")
    assert owner_a.id == owner_b.id
    assert owner_a.handle == "octocat"


def test_handle_collision_gets_a_suffix(db_session):
    first = find_or_create_owner_from_github(db_session, github_id="1", login="dupe")
    second = find_or_create_owner_from_github(db_session, github_id="2", login="dupe")
    assert first.handle == "dupe"
    assert second.handle == "dupe-1"


def test_second_login_revokes_the_first_key(db_session):
    owner = find_or_create_owner_from_github(db_session, github_id="7", login="relogin")

    key1, raw1 = issue_login_key(db_session, owner=owner)
    key2, raw2 = issue_login_key(db_session, owner=owner)

    db_session.refresh(key1)
    assert key1.revoked_at is not None
    assert key2.revoked_at is None
    assert raw1 != raw2


def test_login_redirects_to_github_with_state(client):
    response = client.get("/v1/auth/github/login", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize")
    assert "state=" in location
    assert "redirect_uri=" in location


def test_callback_with_bad_state_redirects_to_error(client):
    response = client.get(
        "/v1/auth/github/callback",
        params={"code": "fake", "state": "not-a-real-state"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers["location"].endswith("/auth/callback#error=1")


def test_state_is_single_use(test_redis):
    state = create_login_state(test_redis)
    assert consume_login_state(test_redis, state) is True
    # Second consume of the same state fails — it was deleted by the first.
    assert consume_login_state(test_redis, state) is False
