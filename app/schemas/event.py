from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class RecurrencePattern(BaseModel):
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    interval: int = Field(ge=1, default=1)  # Interval between recurrences
    end_date: Optional[datetime] = None  # Optional end date for the recurrence
    days_of_week: Optional[List[int]] = None  # 0-6 for Sunday-Saturday, used for weekly recurrence
    day_of_month: Optional[int] = Field(None, ge=1, le=31)  # Used for monthly recurrence
    month_of_year: Optional[int] = Field(None, ge=1, le=12)  # Used for yearly recurrence


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[RecurrencePattern] = None

    @field_validator('is_recurring', mode='before')
    @classmethod
    def validate_is_recurring(cls, v):
        if isinstance(v, str):
            return v.lower() == 'true'
        return bool(v)

    @field_validator('recurrence_pattern')
    @classmethod
    def validate_recurrence_pattern(cls, v, values):
        if values.get('is_recurring') and not v:
            raise ValueError('Recurrence pattern is required when is_recurring is true')
        if not values.get('is_recurring') and v:
            raise ValueError('Recurrence pattern should not be provided when is_recurring is false')
        if v:
            if v.frequency == 'weekly' and not v.days_of_week:
                raise ValueError('days_of_week is required for weekly recurrence')
            if v.frequency == 'monthly' and not v.day_of_month:
                raise ValueError('day_of_month is required for monthly recurrence')
            if v.frequency == 'yearly' and not v.month_of_year:
                raise ValueError('month_of_year is required for yearly recurrence')
        return v


class EventCreate(EventBase):
    pass


class EventUpdate(EventBase):
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class EventPermissionBase(BaseModel):
    user_id: int
    role: str


class EventPermissionCreate(EventPermissionBase):
    pass


class EventPermission(EventPermissionBase):
    id: int
    event_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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