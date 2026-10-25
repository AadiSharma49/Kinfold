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
