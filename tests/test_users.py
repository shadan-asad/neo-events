def test_read_users(client, user_token_headers):
    r = client.get("/api/users/", headers=user_token_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_read_user_me(client, user_token_headers):
    r = client.get("/api/users/me", headers=user_token_headers)
    assert r.status_code == 200
    assert r.json()["email"]

def test_update_user_me(client, user_token_headers):
    update_data = {"username": "updateduser"}
    r = client.put("/api/users/me", json=update_data, headers=user_token_headers)
    assert r.status_code == 200
    assert r.json()["username"] == "updateduser" 