def test_event_permissions(client, user_token_headers):
    # Create event
    event_data = {
        "title": "Perm Event",
        "description": "Event for permissions.",
        "start_time": "2024-06-01T10:00:00Z",
        "end_time": "2024-06-01T12:00:00Z",
        "location": "Perm Location"
    }
    r = client.post("/api/events/", json=event_data, headers=user_token_headers)
    event_id = r.json()["id"]

    # Register another user
    user2 = {"email": "user2@example.com", "username": "user2", "password": "password2"}
    client.post("/api/auth/register", json=user2)
    login_data = {"username": "user2@example.com", "password": "password2"}
    r2 = client.post("/api/auth/login", data=login_data)
    user2_token = r2.json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # Share event
    share_data = {"user_id": 2, "role": "editor"}
    r = client.post(f"/api/events/{event_id}/share", json=share_data, headers=user_token_headers)
    assert r.status_code == 200

    # List permissions
    r = client.get(f"/api/events/{event_id}/permissions", headers=user_token_headers)
    assert r.status_code == 200
    assert any(p["user_id"] == 2 for p in r.json())

    # Remove permission
    r = client.delete(f"/api/events/{event_id}/permissions/2", headers=user_token_headers)
    assert r.status_code == 200
    assert r.json()["msg"] == "Permission removed" 