def test_event_versioning(client, user_token_headers):
    # Create event
    event_data = {
        "title": "Versioned Event",
        "description": "Event for versioning.",
        "start_time": "2024-06-01T10:00:00Z",
        "end_time": "2024-06-01T12:00:00Z",
        "location": "Version Location"
    }
    r = client.post("/api/events/", json=event_data, headers=user_token_headers)
    event_id = r.json()["id"]

    # Update event to create a new version
    update_data = {"title": "Versioned Event Updated"}
    r = client.put(f"/api/events/{event_id}", json=update_data, headers=user_token_headers)
    assert r.status_code == 200

    # List versions
    r = client.get(f"/api/events/{event_id}/history", headers=user_token_headers)
    assert r.status_code == 200
    versions = r.json()
    assert len(versions) >= 2

    # Get a specific version
    version_number = versions[0]["version_number"]
    r = client.get(f"/api/events/{event_id}/history/{version_number}", headers=user_token_headers)
    assert r.status_code == 200
    assert r.json()["version_number"] == version_number

    # Diff versions
    if len(versions) > 1:
        v1 = versions[0]["version_number"]
        v2 = versions[1]["version_number"]
        r = client.get(f"/api/events/{event_id}/diff/{v1}/{v2}", headers=user_token_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), dict) 