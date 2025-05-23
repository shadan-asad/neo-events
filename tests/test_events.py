def test_create_event(client, user_token_headers):
    event_data = {
        "title": "Test Event",
        "description": "A test event.",
        "start_time": "2024-06-01T10:00:00Z",
        "end_time": "2024-06-01T12:00:00Z",
        "location": "Test Location"
    }
    r = client.post("/api/events/", json=event_data, headers=user_token_headers)
    assert r.status_code == 200
    event = r.json()
    assert event["title"] == "Test Event"
    event_id = event["id"]

    # Read event
    r = client.get(f"/api/events/{event_id}", headers=user_token_headers)
    assert r.status_code == 200
    assert r.json()["id"] == event_id

    # Update event
    update_data = {"title": "Updated Event"}
    r = client.put(f"/api/events/{event_id}", json=update_data, headers=user_token_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Updated Event"

    # Delete event
    r = client.delete(f"/api/events/{event_id}", headers=user_token_headers)
    assert r.status_code == 200
    assert r.json()["msg"] == "Event deleted" 