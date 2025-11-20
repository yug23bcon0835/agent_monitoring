from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    model_type = Column(String)
    provider = Column(String)
    meta_info = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    executions = relationship("AgentExecution", back_populates="agent")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "model_type": self.model_type,
            "provider": self.provider,
            "metadata": self.meta_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    input = Column(Text)
    output = Column(Text)
    duration_ms = Column(Float)
    tokens_used = Column(Integer)
    success = Column(Boolean)
    error_message = Column(Text)
    meta_info = Column(JSON, default={})

    agent = relationship("Agent", back_populates="executions")
    metrics = relationship("Metric", back_populates="execution")

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.meta_info,
        }


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String, ForeignKey("agent_executions.id"), nullable=False)
    metric_name = Column(String, nullable=False)
    value = Column(Float)
    tags = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow)

    execution = relationship("AgentExecution", back_populates="metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    benchmark_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String)
    results = Column(JSON, default={})
    meta_info = Column(JSON, default={})

    def to_dict(self):
        return {
            "id": self.id,
            "benchmark_id": self.benchmark_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "results": self.results,
            "metadata": self.meta_info,
        }


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    severity = Column(String)
    message = Column(Text)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String)

    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "severity": self.severity,
            "message": self.message,
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
        }
