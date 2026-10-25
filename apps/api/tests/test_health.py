def test_health_ok(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "database": "ok", "redis": "ok"}
