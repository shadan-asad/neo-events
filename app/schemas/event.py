from typing import Optional, List, Dict, Any, Literal, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator
import json


class RecurrencePattern(BaseModel):
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    interval: int = Field(ge=1, default=1)  # Interval between recurrences
    end_date: Optional[datetime] = None  # Optional end date for the recurrence
    days_of_week: Optional[List[int]] = None  # 0-6 for Sunday-Saturday, used for weekly recurrence
    day_of_month: Optional[int] = Field(None, ge=1, le=31)  # Used for monthly recurrence
    month_of_year: Optional[int] = Field(None, ge=1, le=12)  # Used for yearly recurrence

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is not None:
            # Convert naive datetime to UTC if it's naive
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            
            # Get the event's start time from the parent model
            if 'start_time' in info.data:
                start_time = info.data['start_time']
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                if v <= start_time:
                    raise ValueError('Recurrence end_date must be after the event start_time')
        return v

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        data = super().model_dump(**kwargs)
        if data.get('end_date'):
            data['end_date'] = data['end_date'].isoformat()
        return data

    @classmethod
    def model_validate_json(cls, json_data: str) -> 'RecurrencePattern':
        data = json.loads(json_data)
        if data.get('end_date'):
            data['end_date'] = datetime.fromisoformat(data['end_date'])
        return cls.model_validate(data)


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[RecurrencePattern] = None

    @model_validator(mode='after')
    def validate_dates(self) -> 'EventBase':
        # Convert naive datetimes to UTC
        if self.start_time.tzinfo is None:
            self.start_time = self.start_time.replace(tzinfo=timezone.utc)
        if self.end_time.tzinfo is None:
            self.end_time = self.end_time.replace(tzinfo=timezone.utc)

        # Only validate end time is after start time
        if self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')

        # Validate recurrence pattern if present
        if self.is_recurring and self.recurrence_pattern:
            if self.recurrence_pattern.end_date:
                if self.recurrence_pattern.end_date.tzinfo is None:
                    self.recurrence_pattern.end_date = self.recurrence_pattern.end_date.replace(tzinfo=timezone.utc)
                if self.recurrence_pattern.end_date <= self.start_time:
                    raise ValueError('Recurrence end_date must be after the event start_time')

        return self

    @field_validator('is_recurring', mode='before')
    @classmethod
    def validate_is_recurring(cls, v):
        if isinstance(v, str):
            return v.lower() == 'true'
        return bool(v)

    @field_validator('recurrence_pattern')
    @classmethod
    def validate_recurrence_pattern(cls, v, info):
        if info.data.get('is_recurring') and not v:
            raise ValueError('Recurrence pattern is required when is_recurring is true')
        if not info.data.get('is_recurring') and v:
            raise ValueError('Recurrence pattern should not be provided when is_recurring is false')
        if v:
            if v.frequency == 'weekly' and not v.days_of_week:
                raise ValueError('days_of_week is required for weekly recurrence')
            if v.frequency == 'monthly' and not v.day_of_month:
                raise ValueError('day_of_month is required for monthly recurrence')
            if v.frequency == 'yearly' and not v.month_of_year:
                raise ValueError('month_of_year is required for yearly recurrence')
        return v

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Convert datetime fields to ISO format
        if data.get('start_time'):
            data['start_time'] = data['start_time'].isoformat()
        if data.get('end_time'):
            data['end_time'] = data['end_time'].isoformat()
        if data.get('recurrence_pattern'):
            data['recurrence_pattern'] = self.recurrence_pattern.model_dump()
        return data


class EventCreate(EventBase):
    @model_validator(mode='after')
    def validate_start_time_future(self) -> 'EventCreate':
        # Only validate start time is in future for new events
        current_time = datetime.now(timezone.utc)
        if self.start_time <= current_time:
            raise ValueError('start_time must be in the future')
        return self


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[RecurrencePattern] = None

    @model_validator(mode='after')
    def validate_dates(self) -> 'EventUpdate':
        # Only validate if both start_time and end_time are provided
        if self.start_time is not None and self.end_time is not None:
            # Convert naive datetimes to UTC
            if self.start_time.tzinfo is None:
                self.start_time = self.start_time.replace(tzinfo=timezone.utc)
            if self.end_time.tzinfo is None:
                self.end_time = self.end_time.replace(tzinfo=timezone.utc)

            # Validate end time is after start time
            if self.end_time <= self.start_time:
                raise ValueError('end_time must be after start_time')

        # Validate recurrence pattern if present
        if self.is_recurring and self.recurrence_pattern:
            if self.recurrence_pattern.end_date:
                if self.recurrence_pattern.end_date.tzinfo is None:
                    self.recurrence_pattern.end_date = self.recurrence_pattern.end_date.replace(tzinfo=timezone.utc)
                if self.start_time and self.recurrence_pattern.end_date <= self.start_time:
                    raise ValueError('Recurrence end_date must be after the event start_time')

        return self

    @field_validator('is_recurring', mode='before')
    @classmethod
    def validate_is_recurring(cls, v):
        if isinstance(v, str):
            return v.lower() == 'true'
        return bool(v) if v is not None else None


class EventPermissionBase(BaseModel):
    user_id: int
    role: Literal["owner", "editor", "viewer"]

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ["owner", "editor", "viewer"]:
            raise ValueError('Role must be one of: owner, editor, viewer')
        return v


class EventPermissionCreate(EventPermissionBase):
    pass


class EventPermissionUpdate(BaseModel):
    role: Literal["owner", "editor", "viewer"]

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ["owner", "editor", "viewer"]:
            raise ValueError('Role must be one of: owner, editor, viewer')
        return v


class EventPermission(EventPermissionBase):
    id: int
    event_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventShareRequest(BaseModel):
    users: List[EventPermissionCreate]

    @field_validator('users')
    @classmethod
    def validate_users(cls, v: List[EventPermissionCreate]) -> List[EventPermissionCreate]:
        if not v:
            raise ValueError('At least one user must be provided')
        
        # Check for duplicate user_ids
        user_ids = [user.user_id for user in v]
        if len(user_ids) != len(set(user_ids)):
            raise ValueError('Duplicate user_ids are not allowed')
        
        return v


class EventVersionBase(BaseModel):
    version_number: int
    data: Dict[str, Any]
    comment: Optional[str] = None


class EventVersionCreate(EventVersionBase):
    pass


class EventVersion(BaseModel):
    id: int
    event_id: int
    version_number: int
    data: Dict[str, Any]
    created_by_id: int
    created_at: datetime
    comment: Optional[str] = None
    change_type: str
    changed_fields: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class Event(EventBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[EventPermission] = []
    versions: List[EventVersion] = []

    class Config:
        from_attributes = True


class EventCreateResponse(EventBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[EventPermission] = []

    class Config:
        from_attributes = True


class EventDiff(BaseModel):
    version1: int
    version2: int
    changes: Dict[str, Dict[str, Any]]


class EventList(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[RecurrencePattern] = None
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[EventPermission] = []

    class Config:
        from_attributes = True

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Convert datetime fields to ISO format
        if data.get('start_time'):
            data['start_time'] = data['start_time'].isoformat()
        if data.get('end_time'):
            data['end_time'] = data['end_time'].isoformat()
        if data.get('recurrence_pattern'):
            data['recurrence_pattern'] = self.recurrence_pattern.model_dump()
        return data


class EventBatchCreate(BaseModel):
    events: List[EventCreate]

    @field_validator('events')
    @classmethod
    def validate_events(cls, v: List[EventCreate]) -> List[EventCreate]:
        if not v:
            raise ValueError('At least one event must be provided')
        if len(v) > 100:  # Limit batch size to prevent abuse
            raise ValueError('Maximum 100 events can be created in a single batch')
        return v


class EventBatchResponse(BaseModel):
    created: List[EventCreateResponse]
    failed: List[Dict[str, Any]]  # List of events that failed to create with error messages 


class EventChangelogEntry(BaseModel):
    version_number: int
    timestamp: datetime
    user_id: int
    change_type: str
    comment: Optional[str] = None
    changes: Optional[Dict[str, Union[Dict[str, Any], List[str]]]] = None

    class Config:
        from_attributes = True 