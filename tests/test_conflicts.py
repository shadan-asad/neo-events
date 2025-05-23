def test_event_conflict_detection(client, user_token_headers):
    # Create first event
    event1 = {
        "title": "Event 1",
        "description": "First event.",
        "start_time": "2024-06-01T10:00:00Z",
        "end_time": "2024-06-01T12:00:00Z",
        "location": "Loc 1"
    }
    r = client.post("/api/events/", json=event1, headers=user_token_headers)
    assert r.status_code == 200

    # Create conflicting event
    event2 = {
        "title": "Event 2",
        "description": "Second event.",
        "start_time": "2024-06-01T11:00:00Z",
        "end_time": "2024-06-01T13:00:00Z",
        "location": "Loc 2"
    }
    r = client.post("/api/events/", json=event2, headers=user_token_headers)
    # Should return 400 or conflict error
    assert r.status_code in (400, 409)
    assert "conflict" in r.text.lower() 