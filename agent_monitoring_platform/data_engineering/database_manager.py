from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
import logging

from .data_models import Base, Agent, AgentExecution, Metric, EvaluationRun, Alert


class DatabaseManager:
    def __init__(self, database_url: str = "sqlite:///monitoring.db"):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False)
        self.logger = logging.getLogger(__name__)

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        self.logger.info("Database tables created")

    def get_session(self) -> Session:
        return self.SessionLocal()

    def add_agent(self, name: str, version: str, model_type: str, provider: str, metadata: Optional[Dict] = None) -> Agent:
        session = self.get_session()
        try:
            agent = Agent(
                name=name,
                version=version,
                model_type=model_type,
                provider=provider,
                meta_info=metadata or {},
            )
            session.add(agent)
            session.commit()
            self.logger.info(f"Agent added: {name} v{version}")
            return agent
        finally:
            session.close()

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        session = self.get_session()
        try:
            return session.query(Agent).filter(Agent.id == agent_id).first()
        finally:
            session.close()

    def get_agents(self, name: Optional[str] = None) -> List[Agent]:
        session = self.get_session()
        try:
            query = session.query(Agent)
            if name:
                query = query.filter(Agent.name == name)
            return query.all()
        finally:
            session.close()

    def add_execution(
        self,
        agent_id: str,
        input_data: str,
        output_data: str,
        duration_ms: float,
        tokens_used: int,
        success: bool,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AgentExecution:
        session = self.get_session()
        try:
            execution = AgentExecution(
                agent_id=agent_id,
                input=input_data,
                output=output_data,
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                success=success,
                error_message=error_message,
                meta_info=metadata or {},
            )
            session.add(execution)
            session.commit()
            session.refresh(execution)
            self.logger.info(f"Execution added for agent {agent_id}")
            return execution
        finally:
            session.close()

    def get_executions(self, agent_id: Optional[str] = None, limit: int = 100) -> List[AgentExecution]:
        session = self.get_session()
        try:
            query = session.query(AgentExecution)
            if agent_id:
                query = query.filter(AgentExecution.agent_id == agent_id)
            return query.order_by(AgentExecution.timestamp.desc()).limit(limit).all()
        finally:
            session.close()

    def add_metric(
        self, execution_id: str, metric_name: str, value: float, tags: Optional[Dict] = None
    ) -> Metric:
        session = self.get_session()
        try:
            metric = Metric(
                execution_id=execution_id,
                metric_name=metric_name,
                value=value,
                tags=tags or {},
            )
            session.add(metric)
            session.commit()
            return metric
        finally:
            session.close()

    def get_metrics(self, metric_name: Optional[str] = None, limit: int = 1000) -> List[Metric]:
        session = self.get_session()
        try:
            query = session.query(Metric)
            if metric_name:
                query = query.filter(Metric.metric_name == metric_name)
            return query.order_by(Metric.timestamp.desc()).limit(limit).all()
        finally:
            session.close()

    def add_evaluation_run(
        self,
        benchmark_id: str,
        status: str,
        results: Dict,
        metadata: Optional[Dict] = None,
    ) -> EvaluationRun:
        session = self.get_session()
        try:
            eval_run = EvaluationRun(
                benchmark_id=benchmark_id,
                status=status,
                results=results,
                meta_info=metadata or {},
            )
            session.add(eval_run)
            session.commit()
            session.refresh(eval_run)
            self.logger.info(f"Evaluation run added: {benchmark_id}")
            return eval_run
        finally:
            session.close()

    def get_evaluation_runs(self, benchmark_id: Optional[str] = None, limit: int = 100) -> List[EvaluationRun]:
        session = self.get_session()
        try:
            query = session.query(EvaluationRun)
            if benchmark_id:
                query = query.filter(EvaluationRun.benchmark_id == benchmark_id)
            return query.order_by(EvaluationRun.timestamp.desc()).limit(limit).all()
        finally:
            session.close()

    def add_alert(self, rule_id: str, severity: str, message: str) -> Alert:
        session = self.get_session()
        try:
            alert = Alert(
                rule_id=rule_id,
                severity=severity,
                message=message,
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)
            return alert
        finally:
            session.close()

    def get_alerts(self, severity: Optional[str] = None, limit: int = 100) -> List[Alert]:
        session = self.get_session()
        try:
            query = session.query(Alert)
            if severity:
                query = query.filter(Alert.severity == severity)
            return query.order_by(Alert.timestamp.desc()).limit(limit).all()
        finally:
            session.close()

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        session = self.get_session()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = acknowledged_by
                session.commit()
        finally:
            session.close()

    def cleanup_old_data(self, retention_days: int = 90):
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            session.query(Metric).filter(Metric.timestamp < cutoff_date).delete()
            session.query(AgentExecution).filter(AgentExecution.timestamp < cutoff_date).delete()
            session.query(EvaluationRun).filter(EvaluationRun.timestamp < cutoff_date).delete()
            session.query(Alert).filter(Alert.timestamp < cutoff_date).delete()

            session.commit()
            self.logger.info(f"Cleaned up data older than {retention_days} days")
        finally:
            session.close()

    def get_statistics(self) -> Dict[str, Any]:
        session = self.get_session()
        try:
            return {
                "agents_count": session.query(Agent).count(),
                "executions_count": session.query(AgentExecution).count(),
                "metrics_count": session.query(Metric).count(),
                "evaluation_runs_count": session.query(EvaluationRun).count(),
                "alerts_count": session.query(Alert).count(),
                "unacknowledged_alerts": session.query(Alert).filter(Alert.acknowledged == False).count(),
            }
        finally:
            session.close()

    def backup(self, backup_path: str):
        self.logger.info(f"Backing up database to {backup_path}")

    def close(self):
        self.engine.dispose()
