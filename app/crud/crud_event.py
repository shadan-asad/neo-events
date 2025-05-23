from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.crud.base import CRUDBase
from app.db.models import Event, EventVersion, EventPermission, User, UserRole
from app.schemas.event import EventCreate, EventUpdate, EventVersionCreate


def serialize_datetimes(obj):
    if isinstance(obj, dict):
        return {k: serialize_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetimes(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


class CRUDEvent(CRUDBase[Event, EventCreate, EventUpdate]):
    def create_with_owner(
        self, db: Session, *, obj_in: EventCreate, owner_id: int
    ) -> Event:
        obj_in_data = obj_in.model_dump()
        db_obj = Event(**obj_in_data, owner_id=owner_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # Serialize datetimes in obj_in_data for JSON storage
        version_data = serialize_datetimes(obj_in_data)

        # Create initial version
        version = EventVersion(
            event_id=db_obj.id,
            version_number=1,
            data=version_data,
            created_by_id=owner_id,
            comment="Initial version",
            change_type="create",
            changed_fields={"all": list(obj_in_data.keys())}  # Track all fields for creation
        )
        db.add(version)
        db.commit()
        
        return db_obj

    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        return (
            db.query(self.model)
            .filter(Event.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_events(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        return (
            db.query(self.model)
            .outerjoin(EventPermission)
            .filter(
                or_(
                    Event.owner_id == user_id,
                    and_(
                        EventPermission.user_id == user_id,
                        EventPermission.role.in_([UserRole.OWNER, UserRole.EDITOR, UserRole.VIEWER])
                    )
                )
            )
            .distinct()  # Add distinct to avoid duplicates
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_version(
        self, db: Session, *, event_id: int, data: Dict[str, Any], user_id: int, comment: Optional[str] = None
    ) -> EventVersion:
        # Get the latest version number
        latest_version = (
            db.query(EventVersion)
            .filter(EventVersion.event_id == event_id)
            .order_by(EventVersion.version_number.desc())
            .first()
        )
        version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Get the previous version's data for comparison
        previous_data = latest_version.data if latest_version else {}
        
        # Define essential fields to track
        essential_fields = {
            "title", "description", "start_time", "end_time", 
            "location", "is_recurring", "recurrence_pattern"
        }
        
        # Calculate changed fields, only for essential fields
        changed_fields = {}
        for key in essential_fields:
            if key in data:
                if key not in previous_data or previous_data[key] != data[key]:
                    changed_fields[key] = {
                        "old": previous_data.get(key),
                        "new": data[key]
                    }
        
        # Only store essential event data
        essential_data = {
            "title": data.get("title"),
            "description": data.get("description"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "location": data.get("location"),
            "is_recurring": data.get("is_recurring"),
            "recurrence_pattern": data.get("recurrence_pattern")
        }
        
        # Serialize datetimes in data for JSON storage
        version_data = serialize_datetimes(essential_data)
        changed_fields = serialize_datetimes(changed_fields)
        
        version = EventVersion(
            event_id=event_id,
            version_number=version_number,
            data=version_data,
            created_by_id=user_id,
            comment=comment,
            change_type="update",
            changed_fields=changed_fields
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    def get_version(self, db: Session, *, event_id: int, version_number: int) -> Optional[EventVersion]:
        return (
            db.query(EventVersion)
            .filter(
                and_(
                    EventVersion.event_id == event_id,
                    EventVersion.version_number == version_number
                )
            )
            .first()
        )

    def get_versions(self, db: Session, *, event_id: int) -> List[EventVersion]:
        return (
            db.query(EventVersion)
            .filter(EventVersion.event_id == event_id)
            .order_by(EventVersion.version_number)
            .all()
        )

    def add_permission(
        self, db: Session, *, event_id: int, user_id: int, role: UserRole
    ) -> EventPermission:
        # Check if permission already exists
        existing_permission = (
            db.query(EventPermission)
            .filter(
                and_(
                    EventPermission.event_id == event_id,
                    EventPermission.user_id == user_id
                )
            )
            .first()
        )
        
        if existing_permission:
            # Update existing permission
            existing_permission.role = role
            db.add(existing_permission)
            db.commit()
            db.refresh(existing_permission)
            return existing_permission
        
        # Create new permission
        permission = EventPermission(
            event_id=event_id,
            user_id=user_id,
            role=role
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)
        return permission

    def get_permissions(self, db: Session, *, event_id: int) -> List[EventPermission]:
        return (
            db.query(EventPermission)
            .filter(EventPermission.event_id == event_id)
            .all()
        )

    def remove_permission(
        self, db: Session, *, event_id: int, user_id: int
    ) -> Optional[EventPermission]:
        permission = (
            db.query(EventPermission)
            .filter(
                and_(
                    EventPermission.event_id == event_id,
                    EventPermission.user_id == user_id
                )
            )
            .first()
        )
        if permission:
            db.delete(permission)
            db.commit()
        return permission

    def update_permission(
        self, db: Session, *, event_id: int, user_id: int, role: UserRole
    ) -> Optional[EventPermission]:
        permission = (
            db.query(EventPermission)
            .filter(
                and_(
                    EventPermission.event_id == event_id,
                    EventPermission.user_id == user_id
                )
            )
            .first()
        )
        if permission:
            permission.role = role
            db.add(permission)
            db.commit()
            db.refresh(permission)
        return permission

    def check_permission(
        self, db: Session, *, event_id: int, user_id: int, required_role: UserRole
    ) -> bool:
        event = self.get(db, id=event_id)
        if not event:
            return False
        
        if event.owner_id == user_id:
            return True
        
        permission = (
            db.query(EventPermission)
            .filter(
                and_(
                    EventPermission.event_id == event_id,
                    EventPermission.user_id == user_id
                )
            )
            .first()
        )
        
        if not permission:
            return False
            
        role_hierarchy = {
            UserRole.OWNER: 3,
            UserRole.EDITOR: 2,
            UserRole.VIEWER: 1
        }
        
        return role_hierarchy[permission.role] >= role_hierarchy[required_role]

    def check_conflicts(
        self, db: Session, *, event_id: int, start_time: datetime, end_time: datetime
    ) -> List[Event]:
        return (
            db.query(self.model)
            .filter(
                and_(
                    Event.id != event_id,
                    or_(
                        and_(
                            Event.start_time <= start_time,
                            Event.end_time > start_time
                        ),
                        and_(
                            Event.start_time < end_time,
                            Event.end_time >= end_time
                        ),
                        and_(
                            Event.start_time >= start_time,
                            Event.end_time <= end_time
                        )
                    )
                )
            )
            .all()
        )

    def create_batch(
        self, db: Session, *, events: List[EventCreate], owner_id: int
    ) -> Dict[str, List[Any]]:
        """
        Create multiple events in a single transaction.
        Returns a dictionary with lists of successfully created events and failed events with error messages.
        """
        created_events = []
        failed_events = []

        for event in events:
            try:
                # Check for conflicts
                conflicts = self.check_conflicts(
                    db,
                    event_id=0,  # New event
                    start_time=event.start_time,
                    end_time=event.end_time
                )
                if conflicts:
                    failed_events.append({
                        "event": event.model_dump(),
                        "error": "Event conflicts with existing events"
                    })
                    continue

                # Create the event
                db_obj = self.create_with_owner(
                    db=db,
                    obj_in=event,
                    owner_id=owner_id
                )
                created_events.append(db_obj)

            except ValueError as e:
                failed_events.append({
                    "event": event.model_dump(),
                    "error": str(e)
                })
            except Exception as e:
                failed_events.append({
                    "event": event.model_dump(),
                    "error": f"Unexpected error: {str(e)}"
                })

        return {
            "created": created_events,
            "failed": failed_events
        }


event = CRUDEvent(Event) 