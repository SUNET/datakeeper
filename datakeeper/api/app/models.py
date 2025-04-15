from sqlalchemy.sql import func
from datakeeper.api.app.db import Base
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    CheckConstraint,
    DateTime,
    Text,
)


class Policy(Base):
    __tablename__ = 'policy'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    policy_file = Column(String, nullable=False)
    is_enabled = Column(Integer, CheckConstraint('is_enabled IN (0, 1)'), nullable=False)
    strategy = Column(String, nullable=False)
    data_type = Column(Text, CheckConstraint('json_valid(data_type)'), nullable=False)
    tags = Column(Text, CheckConstraint('json_valid(tags)'), nullable=False)
    paths = Column(Text, CheckConstraint('json_valid(paths)'), nullable=False)
    operations = Column(Text, CheckConstraint('json_valid(operations)'), nullable=False)
    triggers = Column(Text, CheckConstraint('json_valid(triggers)'), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp())


class Job(Base):
    __tablename__ = 'job'
    
    id = Column(String, primary_key=True)
    policy_id = Column(String, ForeignKey('policy.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    filetypes = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False)
    trigger_spec = Column(Text, CheckConstraint('json_valid(trigger_spec)'), nullable=False)
    status = Column(String, CheckConstraint("status IN ('added', 'scheduled', 'running', 'success', 'failed')"))
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    last_run_time = Column(DateTime, nullable=True)
