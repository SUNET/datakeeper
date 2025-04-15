

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, field_validator, field_serializer

class PolicyBase(BaseModel):
    name: str
    policy_file: str
    is_enabled: int
    strategy: str
    data_type: List[str] = Field(...)  # JSON field
    tags: List[str] = Field(...)  # JSON field
    paths: List[str] = Field(...)  # JSON field
    operations: List[str] = Field(...)  # JSON field
    triggers: List[Dict[str, Any]] = Field(...)  # JSON field

    @validator('is_enabled')
    def validate_is_enabled(cls, v):
        if v not in (0, 1):
            raise ValueError('is_enabled must be 0 or 1')
        return v
    
    @validator('data_type', 'tags', 'paths', 'operations', 'triggers', pre=True)
    def parse_json(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON string: {value}")
        return value


class PolicyCreate(PolicyBase):
    id: str


class PolicyResponseModel(PolicyBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobBase(BaseModel):
    name: str
    operation: str
    filetypes: str
    trigger_type: str
    trigger_spec: Dict[str, Any] = Field(...)  # JSON field




class JobCreate(JobBase):
    id: str
    policy_id: str


class JobResponseModel(JobBase):
    id: str
    policy_id: str
    status: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    last_run_time: Optional[datetime] = None

    @field_validator('status')
    def validate_status(cls, v):
        if v is not None and v not in ('added', 'scheduled', 'running', 'success', 'failed'):
            raise ValueError('status must be one of: added, scheduled, running, success, failed')
        return v

    
    @field_validator('trigger_spec', mode="before")
    def parse_json(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON string: {value}")
        return value
    
    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime, _info):
        return created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    @field_serializer('last_run_time')
    def serialize_last_run_time(self, last_run_time: datetime, _info):
        return last_run_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    class Config:
        from_attributes = True
