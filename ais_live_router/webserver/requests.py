

import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field, validator

class PolicyBase(BaseModel):
    is_enabled: int
    data_type: List[str] = Field(...)  # JSON field
    tags: List[str] = Field(...)  # JSON field

    @validator('is_enabled')
    def validate_is_enabled(cls, v):
        if v not in (0, 1):
            raise ValueError('is_enabled must be 0 or 1')
        return v
    
    @validator('data_type', 'tags', pre=True)
    def parse_json(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON string: {value}")
        return value

class JobBase(BaseModel):
    name: str
    trigger_spec: Dict[str, Any] = Field(...)
