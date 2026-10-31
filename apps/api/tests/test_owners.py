def test_dev_signup_returns_key_once_and_it_works(client):
    response = client.post("/v1/owners/dev-signup", json={"handle": "ada"})
    assert response.status_code == 201
    body = response.json()

    assert body["owner"]["handle"] == "ada"
    raw_key = body["key"]["key"]
    assert raw_key.startswith("kf_owner_")
    assert "warning" in body["key"]

    me = client.get("/v1/owners/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert me.status_code == 200
    assert me.json()["handle"] == "ada"


def test_dev_signup_rejects_duplicate_handle(client):
    client.post("/v1/owners/dev-signup", json={"handle": "grace"})
    response = client.post("/v1/owners/dev-signup", json={"handle": "grace"})
    assert response.status_code == 409


def test_dev_signup_setting_defaults_to_off():
    """The real safety net is this default, not .env.example (which turns
    it on for local convenience) or docs/deploy-checklist.md (which tells
    the operator to set it false) — if someone deploys with no .env.api
    file at all, Settings() must still come up with dev-signup disabled."""
    from kinfold_api.config import Settings

    assert Settings.model_fields["KINFOLD_DEV_SIGNUP"].default is False


def test_dev_signup_route_is_a_404_when_disabled(client, monkeypatch):
    from kinfold_api.config import get_settings

    monkeypatch.setattr(get_settings(), "KINFOLD_DEV_SIGNUP", False)
    response = client.post("/v1/owners/dev-signup", json={"handle": "should_not_work"})
    assert response.status_code == 404
