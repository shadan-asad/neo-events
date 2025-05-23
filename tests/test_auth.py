def test_register_and_login(client):
    user_data = {"email": "user1@example.com", "username": "user1", "password": "password1"}
    r = client.post("/api/auth/register", json=user_data)
    assert r.status_code == 200
    # Try logging in
    login_data = {"username": "user1@example.com", "password": "password1"}
    r = client.post("/api/auth/login", data=login_data)
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "refresh_token" in r.json()

def test_refresh_token(client):
    user_data = {"email": "user2@example.com", "username": "user2", "password": "password2"}
    client.post("/api/auth/register", json=user_data)
    login_data = {"username": "user2@example.com", "password": "password2"}
    r = client.post("/api/auth/login", data=login_data)
    refresh_token = r.json()["refresh_token"]
    r = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()

def test_logout(client, user_token_headers):
    r = client.post("/api/auth/logout", headers=user_token_headers)
    assert r.status_code == 200
    assert r.json()["msg"] == "Successfully logged out" 