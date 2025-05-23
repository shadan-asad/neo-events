from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_event
from app.db.models import UserRole, User as DBUser
from app.schemas.event import (
    Event,
    EventCreate,
    EventUpdate,
    EventPermission,
    EventPermissionCreate,
    EventVersion,
    EventDiff,
    EventCreateResponse,
    EventShareRequest
)
from app.schemas.user import User

router = APIRouter()


@router.post("", response_model=EventCreateResponse)
def create_event(
    *,
    db: Session = Depends(deps.get_db),
    event_in: EventCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a new event.

    The event can be either a one-time event or a recurring event. For recurring events, a recurrence pattern must be provided.

    Request Body Examples:

    1. One-time event:
    ```json
    {
        "title": "Team Meeting",
        "description": "Weekly sync with the team",
        "start_time": "2024-03-20T10:00:00Z",
        "end_time": "2024-03-20T11:00:00Z",
        "location": "Conference Room A",
        "is_recurring": false
    }
    ```

    2. Daily recurring event:
    ```json
    {
        "title": "Daily Standup",
        "description": "Daily team standup meeting",
        "start_time": "2024-03-20T09:00:00Z",
        "end_time": "2024-03-20T09:30:00Z",
        "is_recurring": true,
        "recurrence_pattern": {
            "frequency": "daily",
            "interval": 1,
            "end_date": "2024-12-31T23:59:59Z"
        }
    }
    ```

    3. Weekly recurring event:
    ```json
    {
        "title": "Weekly Team Meeting",
        "description": "Regular team sync",
        "start_time": "2024-03-20T10:00:00Z",
        "end_time": "2024-03-20T11:00:00Z",
        "is_recurring": true,
        "recurrence_pattern": {
            "frequency": "weekly",
            "interval": 1,
            "days_of_week": [2, 4],
            "end_date": "2024-12-31T23:59:59Z"
        }
    }
    ```

    4. Monthly recurring event:
    ```json
    {
        "title": "Monthly Review",
        "description": "Monthly project review meeting",
        "start_time": "2024-03-20T14:00:00Z",
        "end_time": "2024-03-20T15:00:00Z",
        "is_recurring": true,
        "recurrence_pattern": {
            "frequency": "monthly",
            "interval": 1,
            "day_of_month": 15,
            "end_date": "2024-12-31T23:59:59Z"
        }
    }
    ```

    5. Yearly recurring event:
    ```json
    {
        "title": "Annual Review",
        "description": "Annual performance review",
        "start_time": "2024-03-20T09:00:00Z",
        "end_time": "2024-03-20T17:00:00Z",
        "is_recurring": true,
        "recurrence_pattern": {
            "frequency": "yearly",
            "interval": 1,
            "month_of_year": 12,
            "end_date": "2024-12-31T23:59:59Z"
        }
    }
    ```

    Response Example:
    ```json
    {
        "id": 1,
        "title": "Team Meeting",
        "description": "Weekly sync with the team",
        "start_time": "2024-03-20T10:00:00Z",
        "end_time": "2024-03-20T11:00:00Z",
        "location": "Conference Room A",
        "is_recurring": false,
        "owner_id": 1,
        "created_at": "2024-03-20T09:00:00Z",
        "updated_at": "2024-03-20T09:00:00Z",
        "permissions": []
    }
    ```

    Error Responses:
    1. Conflict with existing event:
    ```json
    {
        "detail": "Event conflicts with existing events"
    }
    ```

    2. Invalid recurrence pattern:
    ```json
    {
        "detail": "Recurrence pattern is required when is_recurring is true"
    }
    ```

    3. Invalid time range:
    ```json
    {
        "detail": "End time must be after start time"
    }
    ```

    Notes:
    - For recurring events, `is_recurring` must be true and `recurrence_pattern` must be provided
    - For weekly recurrence, `days_of_week` is required (0-6 for Sunday-Saturday)
    - For monthly recurrence, `day_of_month` is required (1-31)
    - For yearly recurrence, `month_of_year` is required (1-12)
    - `interval` defaults to 1 if not provided
    - `end_date` is optional for all recurrence types
    - `end_time` must be after `start_time`
    """
    try:
        # Check for conflicts
        conflicts = crud_event.event.check_conflicts(
            db,
            event_id=0,  # New event
            start_time=event_in.start_time,
            end_time=event_in.end_time
        )
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event conflicts with existing events"
            )
        
        event = crud_event.event.create_with_owner(
            db=db, obj_in=event_in, owner_id=current_user.id
        )
        return event
    except ValueError as e:
        error_message = str(e)
        if "end_time must be after start_time" in error_message:
            error_message = "End time must be after start time"
        elif "Recurrence pattern is required" in error_message:
            error_message = "Recurrence pattern is required when is_recurring is true"
        elif "days_of_week is required" in error_message:
            error_message = "Days of week are required for weekly recurrence"
        elif "day_of_month is required" in error_message:
            error_message = "Day of month is required for monthly recurrence"
        elif "month_of_year is required" in error_message:
            error_message = "Month of year is required for yearly recurrence"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )


@router.get("", response_model=List[Event])
def read_events(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve events.

    Returns a list of events that the current user has access to (either as owner or through permissions).
    Results are paginated using skip and limit parameters.

    Query Parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 100, max: 100)

    Response Example:
    ```json
    [
        {
            "id": 1,
            "title": "Team Meeting",
            "description": "Weekly sync with the team",
            "start_time": "2024-03-20T10:00:00Z",
            "end_time": "2024-03-20T11:00:00Z",
            "location": "Conference Room A",
            "is_recurring": false,
            "owner_id": 1,
            "created_at": "2024-03-20T09:00:00Z",
            "updated_at": "2024-03-20T09:00:00Z",
            "permissions": [
                {
                    "id": 1,
                    "user_id": 2,
                    "role": "editor",
                    "event_id": 1,
                    "created_at": "2024-03-20T09:00:00Z",
                    "updated_at": "2024-03-20T09:00:00Z"
                }
            ]
        }
    ]
    ```

    Error Responses:
    1. Invalid pagination parameters:
    ```json
    {
        "detail": "Limit must be between 1 and 100"
    }
    ```
    """
    events = crud_event.event.get_user_events(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return events


@router.get("/{event_id}", response_model=Event)
def read_event(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get event by ID.

    Returns the details of a specific event if the current user has at least viewer permission.

    Path Parameters:
    - event_id: ID of the event to retrieve

    Response Example:
    ```json
    {
        "id": 1,
        "title": "Team Meeting",
        "description": "Weekly sync with the team",
        "start_time": "2024-03-20T10:00:00Z",
        "end_time": "2024-03-20T11:00:00Z",
        "location": "Conference Room A",
        "is_recurring": false,
        "owner_id": 1,
        "created_at": "2024-03-20T09:00:00Z",
        "updated_at": "2024-03-20T09:00:00Z",
        "permissions": [
            {
                "id": 1,
                "user_id": 2,
                "role": "editor",
                "event_id": 1,
                "created_at": "2024-03-20T09:00:00Z",
                "updated_at": "2024-03-20T09:00:00Z"
            }
        ]
    }
    ```

    Error Responses:
    1. Event not found:
    ```json
    {
        "detail": "Event not found"
    }
    ```

    2. Insufficient permissions:
    ```json
    {
        "detail": "Not enough permissions"
    }
    """
    event = crud_event.event.get(db=db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not crud_event.event.check_permission(
        db=db, event_id=event_id, user_id=current_user.id, required_role=UserRole.VIEWER
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return event


@router.put("/{event_id}", response_model=Event)
def update_event(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    event_in: EventUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update an event.

    Updates an existing event. The current user must have editor permission.
    Only the fields provided in the request will be updated.

    Path Parameters:
    - event_id: ID of the event to update

    Request Body Examples:

    1. Update title and description:
    ```json
    {
        "title": "Updated Team Meeting",
        "description": "Updated description"
    }
    ```

    2. Update time and location:
    ```json
    {
        "start_time": "2024-03-21T10:00:00Z",
        "end_time": "2024-03-21T11:00:00Z",
        "location": "Conference Room B"
    }
    ```

    3. Convert to recurring event:
    ```json
    {
        "is_recurring": true,
        "recurrence_pattern": {
            "frequency": "weekly",
            "interval": 1,
            "days_of_week": [2, 4],
            "end_date": "2024-12-31T23:59:59Z"
        }
    }
    ```

    4. Update all fields:
    ```json
    {
        "title": "Updated Team Meeting",
        "description": "Updated description",
        "start_time": "2024-03-21T10:00:00Z",
        "end_time": "2024-03-21T11:00:00Z",
        "location": "Conference Room B",
        "is_recurring": true,
        "recurrence_pattern": {
            "frequency": "weekly",
            "interval": 1,
            "days_of_week": [2, 4],
            "end_date": "2024-12-31T23:59:59Z"
        }
    }
    ```

    Response Example:
    ```json
    {
        "id": 1,
        "title": "Updated Team Meeting",
        "description": "Updated description",
        "start_time": "2024-03-21T10:00:00Z",
        "end_time": "2024-03-21T11:00:00Z",
        "location": "Conference Room B",
        "is_recurring": true,
        "recurrence_pattern": {
            "frequency": "weekly",
            "interval": 1,
            "days_of_week": [2, 4],
            "end_date": "2024-12-31T23:59:59Z"
        },
        "owner_id": 1,
        "created_at": "2024-03-20T09:00:00Z",
        "updated_at": "2024-03-20T09:00:00Z",
        "permissions": [
            {
                "id": 1,
                "user_id": 2,
                "role": "editor",
                "event_id": 1,
                "created_at": "2024-03-20T09:00:00Z",
                "updated_at": "2024-03-20T09:00:00Z"
            }
        ]
    }
    ```

    Error Responses:
    1. Event not found:
    ```json
    {
        "detail": "Event not found"
    }
    ```

    2. Insufficient permissions:
    ```json
    {
        "detail": "Not enough permissions"
    }
    ```

    3. Conflict with existing event:
    ```json
    {
        "detail": "Event conflicts with existing events"
    }
    ```

    4. Invalid recurrence pattern:
    ```json
    {
        "detail": "Recurrence pattern is required when is_recurring is true"
    }
    ```

    Notes:
    - All fields are optional in the update request
    - Only provided fields will be updated
    - The same recurrence pattern validation rules apply as in event creation
    """
    event = crud_event.event.get(db=db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not crud_event.event.check_permission(
        db=db, event_id=event_id, user_id=current_user.id, required_role=UserRole.EDITOR
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Check for conflicts
    if event_in.start_time or event_in.end_time:
        conflicts = crud_event.event.check_conflicts(
            db,
            event_id=event_id,
            start_time=event_in.start_time or event.start_time,
            end_time=event_in.end_time or event.end_time
        )
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event conflicts with existing events"
            )
    
    # Create new version
    from app.schemas.event import Event as EventSchema
    event_data = EventSchema.model_validate(event).model_dump()
    update_data = event_in.model_dump(exclude_unset=True)
    event_data.update(update_data)
    crud_event.event.create_version(
        db=db,
        event_id=event_id,
        data=event_data,
        user_id=current_user.id,
        comment="Event updated"
    )
    
    event = crud_event.event.update(db=db, db_obj=event, obj_in=event_in)
    return event


@router.delete("/{event_id}")
def delete_event(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete an event.

    Deletes an event. The current user must be the owner of the event.

    Path Parameters:
    - event_id: ID of the event to delete

    Response Example:
    ```json
    {
        "msg": "Event deleted"
    }
    ```

    Error Responses:
    1. Event not found:
    ```json
    {
        "detail": "Event not found"
    }
    ```

    2. Insufficient permissions:
    ```json
    {
        "detail": "Not enough permissions"
    }
    ```
    """
    event = crud_event.event.get(db=db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not crud_event.event.check_permission(
        db=db, event_id=event_id, user_id=current_user.id, required_role=UserRole.OWNER
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud_event.event.remove(db=db, id=event_id)
    return {"msg": "Event deleted"}


@router.post("/{event_id}/share", response_model=List[EventPermission])
def share_event(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    share_request: EventShareRequest,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Share event with multiple users.

    Shares an event with multiple users by assigning them roles (owner, editor, or viewer).
    The current user must be the owner of the event.

    Path Parameters:
    - event_id: ID of the event to share

    Request Body Example:
    ```json
    {
        "users": [
            {
                "user_id": 2,
                "role": "editor"
            },
            {
                "user_id": 3,
                "role": "viewer"
            }
        ]
    }
    ```

    Response Example:
    ```json
    [
        {
            "id": 1,
            "user_id": 2,
            "role": "editor",
            "event_id": 1,
            "created_at": "2024-03-20T09:00:00Z",
            "updated_at": "2024-03-20T09:00:00Z"
        },
        {
            "id": 2,
            "user_id": 3,
            "role": "viewer",
            "event_id": 1,
            "created_at": "2024-03-20T09:00:00Z",
            "updated_at": "2024-03-20T09:00:00Z"
        }
    ]
    ```

    Error Responses:
    1. Event not found:
    ```json
    {
        "detail": "Event not found"
    }
    ```

    2. Insufficient permissions:
    ```json
    {
        "detail": "Not enough permissions"
    }
    ```

    3. Invalid role:
    ```json
    {
        "detail": "Role must be one of: owner, editor, viewer"
    }
    ```

    4. User not found:
    ```json
    {
        "detail": "User not found"
    }
    ```

    5. Duplicate users:
    ```json
    {
        "detail": "Duplicate user_ids are not allowed"
    }
    ```

    6. Empty users list:
    ```json
    {
        "detail": "At least one user must be provided"
    }
    ```

    Notes:
    - role must be one of: "owner", "editor", "viewer"
    - The users being shared with must exist in the system
    - Duplicate user_ids are not allowed
    - At least one user must be provided
    """
    event = crud_event.event.get(db=db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not crud_event.event.check_permission(
        db=db, event_id=event_id, user_id=current_user.id, required_role=UserRole.OWNER
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Add permissions for each user
    permissions = []
    for user_permission in share_request.users:
        # Check if user exists
        user = db.query(DBUser).filter(DBUser.id == user_permission.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_permission.user_id} not found"
            )
        
        # Convert the role string to lowercase and create the UserRole enum
        role_str = user_permission.role.lower()
        if role_str not in ["owner", "editor", "viewer"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be one of: owner, editor, viewer"
            )
        role = UserRole(role_str)  # Create enum with lowercase value
        permission = crud_event.event.add_permission(
            db=db,
            event_id=event_id,
            user_id=user_permission.user_id,
            role=role  # Pass the enum object
        )
        permissions.append(permission)
    
    return permissions


@router.get("/{event_id}/permissions", response_model=List[EventPermission])
def read_event_permissions(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get event permissions.

    Returns a list of all permissions for an event.
    The current user must have at least viewer permission.

    Path Parameters:
    - event_id: ID of the event to get permissions for

    Response Example:
    ```json
    [
        {
            "id": 1,
            "user_id": 2,
            "role": "editor",
            "event_id": 1,
            "created_at": "2024-03-20T09:00:00Z",
            "updated_at": "2024-03-20T09:00:00Z"
        },
        {
            "id": 2,
            "user_id": 3,
            "role": "viewer",
            "event_id": 1,
            "created_at": "2024-03-20T09:00:00Z",
            "updated_at": "2024-03-20T09:00:00Z"
        }
    ]
    ```

    Error Responses:
    1. Event not found:
    ```json
    {
        "detail": "Event not found"
    }
    ```

    2. Insufficient permissions:
    ```json
    {
        "detail": "Not enough permissions"
    }
    ```
    """
    event = crud_event.event.get(db=db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not crud_event.event.check_permission(
        db=db, event_id=event_id, user_id=current_user.id, required_role=UserRole.VIEWER
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    permissions = crud_event.event.get_permissions(db=db, event_id=event_id)
    return permissions


@router.delete("/{event_id}/permissions/{user_id}")
def remove_event_permission(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    user_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Remove user's permission for an event.

    Removes a user's permission for an event.
    The current user must be the owner of the event.

    Path Parameters:
    - event_id: ID of the event
    - user_id: ID of the user whose permission to remove

    Response Example:
    ```json
    {
        "msg": "Permission removed"
    }
    ```

    Error Responses:
    1. Event not found:
    ```json
    {
        "detail": "Event not found"
    }
    ```

    2. Insufficient permissions:
    ```json
    {
        "detail": "Not enough permissions"
    }
    ```

    3. Permission not found:
    ```json
    {
        "detail": "Permission not found"
    }
    ```
    """
    event = crud_event.event.get(db=db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not crud_event.event.check_permission(
        db=db, event_id=event_id, user_id=current_user.id, required_role=UserRole.OWNER
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    permission = crud_event.event.remove_permission(
        db=db, event_id=event_id, user_id=user_id
    )
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    return {"msg": "Permission removed"}


@router.get("/{event_id}/history", response_model=List[EventVersion])
def read_event_history(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get event version history.

    Returns a list of all versions of an event.
    The current user must have at least viewer permission.

    Path Parameters:
    - event_id: ID of the event to get history for

    Response Example:
    ```json
    [
        {
            "id": 1,
            "event_id": 1,
            "version_number": 1,
            "data": {
                "title": "Original Title",
                "description": "Original description",
                "start_time": "2024-03-20T10:00:00Z",
                "end_time": "2024-03-20T11:00:00Z",
                "location": "Conference Room A",
                "is_recurring": false
            },
            "created_by_id": 1,
            "created_at": "2024-03-20T09:00:00Z",
            "comment": "Event created",
            "change_type": "create",
            "changed_fields": null
        },
        {
            "id": 2,
            "event_id": 1,
            "version_number": 2,
            "data": {
                "title": "Updated Title",
                "description": "Updated description",
                "start_time": "2024-03-20T10:00:00Z",
                "end_time": "2024-03-20T11:00:00Z",
                "location": "Conference Room B",
                "is_recurring": false
            },
            "created_by_id": 1,
            "created_at": "2024-03-20T10:00:00Z",
            "comment": "Event updated",
            "change_type": "update",
            "changed_fields": {
                "title": "Updated Title",
                "description": "Updated description",
                "location": "Conference Room B"
            }
        }
    ]
    ```

    Error Responses:
    1. Event not found:
    ```json
    {
        "detail": "Event not found"
    }
    ```

    2. Insufficient permissions:
    ```json
    {
        "detail": "Not enough permissions"
    }
    ```
    """
    event = crud_event.event.get(db=db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not crud_event.event.check_permission(
        db=db, event_id=event_id, user_id=current_user.id, required_role=UserRole.VIEWER
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    versions = crud_event.event.get_versions(db=db, event_id=event_id)
    return versions


@router.get("/{event_id}/history/{version_id}", response_model=EventVersion)
def read_event_version(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    version_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get specific event version.

    Returns a specific version of an event.
    The current user must have at least viewer permission.

    Path Parameters:
    - event_id: ID of the event
    - version_id: Version number to retrieve

    Response Example:
    ```json
    {
        "id": 2,
        "event_id": 1,
        "version_number": 2,
        "data": {
            "title": "Updated Title",
            "description": "Updated description",
            "start_time": "2024-03-20T10:00:00Z",
            "end_time": "2024-03-20T11:00:00Z",
            "location": "Conference Room B",
            "is_recurring": false
        },
        "created_by_id": 1,
        "created_at": "2024-03-20T10:00:00Z",
        "comment": "Event updated",
        "change_type": "update",
        "changed_fields": {
            "title": "Updated Title",
            "description": "Updated description",
            "location": "Conference Room B"
        }
    }
    ```

    Error Responses:
    1. Event not found:
    ```json
    {
        "detail": "Event not found"
    }
    ```

    2. Version not found:
    ```json
    {
        "detail": "Version not found"
    }
    ```

    3. Insufficient permissions:
    ```json
    {
        "detail": "Not enough permissions"
    }
    ```
    """
    event = crud_event.event.get(db=db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not crud_event.event.check_permission(
        db=db, event_id=event_id, user_id=current_user.id, required_role=UserRole.VIEWER
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    version = crud_event.event.get_version(
        db=db, event_id=event_id, version_number=version_id
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.get("/{event_id}/diff/{version1}/{version2}", response_model=EventDiff)
def get_version_diff(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    version1: int,
    version2: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get diff between two versions.

    Returns the differences between two versions of an event.
    The current user must have at least viewer permission.

    Path Parameters:
    - event_id: ID of the event
    - version1: First version number to compare
    - version2: Second version number to compare

    Response Examples:

    1. Simple field changes:
    ```json
    {
        "version1": 1,
        "version2": 2,
        "changes": {
            "title": {
                "old": "Original Title",
                "new": "Updated Title"
            },
            "description": {
                "old": "Original description",
                "new": "Updated description"
            }
        }
    }
    ```

    2. Complex changes including recurrence:
    ```json
    {
        "version1": 2,
        "version2": 3,
        "changes": {
            "is_recurring": {
                "old": false,
                "new": true
            },
            "recurrence_pattern": {
                "old": null,
                "new": {
                    "frequency": "weekly",
                    "interval": 1,
                    "days_of_week": [2, 4],
                    "end_date": "2024-12-31T23:59:59Z"
                }
            }
        }
    }
    ```

    Error Responses:
    1. Event not found:
    ```json
    {
        "detail": "Event not found"
    }
    ```

    2. Version not found:
    ```json
    {
        "detail": "Version not found"
    }
    ```

    3. Insufficient permissions:
    ```json
    {
        "detail": "Not enough permissions"
    }
    ```
    """
    event = crud_event.event.get(db=db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not crud_event.event.check_permission(
        db=db, event_id=event_id, user_id=current_user.id, required_role=UserRole.VIEWER
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    v1 = crud_event.event.get_version(db=db, event_id=event_id, version_number=version1)
    v2 = crud_event.event.get_version(db=db, event_id=event_id, version_number=version2)
    
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Calculate diff
    changes = {}
    for key in set(v1.data.keys()) | set(v2.data.keys()):
        if key not in v1.data:
            changes[key] = {"old": None, "new": v2.data[key]}
        elif key not in v2.data:
            changes[key] = {"old": v1.data[key], "new": None}
        elif v1.data[key] != v2.data[key]:
            changes[key] = {"old": v1.data[key], "new": v2.data[key]}
    
    return EventDiff(version1=version1, version2=version2, changes=changes) 