from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import logging

from .database_manager import DatabaseManager


@dataclass
class ETLJob:
    job_id: str
    status: str
    source_type: str
    record_count: int
    timestamp: datetime
    error: Optional[str] = None


class ETLPipeline:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.transformers: Dict[str, Callable] = {}
        self.jobs: List[ETLJob] = []

    def register_transformer(self, name: str, transform_func: Callable):
        self.transformers[name] = transform_func

    def extract(self, source: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
        self.logger.info(f"Extracting from {source}")

        if source == "executions":
            executions = self.db_manager.get_executions(limit=1000)
            return [e.to_dict() for e in executions]
        elif source == "metrics":
            metrics = self.db_manager.get_metrics(limit=1000)
            return [m.to_dict() for m in metrics]
        elif source == "evaluations":
            evals = self.db_manager.get_evaluation_runs(limit=1000)
            return [e.to_dict() for e in evals]
        elif source == "agents":
            agents = self.db_manager.get_agents()
            return [a.to_dict() for a in agents]

        return []

    def transform(self, data: List[Dict[str, Any]], transformer_name: Optional[str] = None) -> List[Dict[str, Any]]:
        self.logger.info(f"Transforming {len(data)} records")

        transformed_data = []
        for record in data:
            try:
                transformed_record = self._transform_record(record, transformer_name)
                if transformed_record:
                    transformed_data.append(transformed_record)
            except Exception as e:
                self.logger.error(f"Error transforming record: {e}")

        return transformed_data

    def _transform_record(self, record: Dict[str, Any], transformer_name: Optional[str]) -> Optional[Dict[str, Any]]:
        if transformer_name and transformer_name in self.transformers:
            return self.transformers[transformer_name](record)

        return record

    def load(self, data: List[Dict[str, Any]], target: str) -> bool:
        self.logger.info(f"Loading {len(data)} records to {target}")

        try:
            for record in data:
                if target == "metrics":
                    self.db_manager.add_metric(
                        execution_id=record.get("execution_id"),
                        metric_name=record.get("metric_name"),
                        value=record.get("value", 0),
                        tags=record.get("tags", {}),
                    )
                elif target == "executions":
                    self.db_manager.add_execution(
                        agent_id=record.get("agent_id"),
                        input_data=record.get("input", ""),
                        output_data=record.get("output", ""),
                        duration_ms=record.get("duration_ms", 0),
                        tokens_used=record.get("tokens_used", 0),
                        success=record.get("success", False),
                        error_message=record.get("error_message"),
                    )

            return True
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            return False

    def validate(self, data: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
        errors = []

        for i, record in enumerate(data):
            if not record:
                errors.append(f"Record {i}: Empty record")
            if not isinstance(record, dict):
                errors.append(f"Record {i}: Not a dictionary")

        return len(errors) == 0, errors

    def run_pipeline(self, source: str, target: str, transformer: Optional[str] = None) -> ETLJob:
        job_id = f"etl_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        try:
            data = self.extract(source)
            is_valid, validation_errors = self.validate(data)

            if not is_valid:
                self.logger.warning(f"Validation errors: {validation_errors}")

            transformed_data = self.transform(data, transformer)
            success = self.load(transformed_data, target)

            job = ETLJob(
                job_id=job_id,
                status="SUCCESS" if success else "FAILED",
                source_type=source,
                record_count=len(transformed_data),
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            job = ETLJob(
                job_id=job_id,
                status="ERROR",
                source_type=source,
                record_count=0,
                timestamp=datetime.utcnow(),
                error=str(e),
            )
            self.logger.error(f"Pipeline error: {e}")

        self.jobs.append(job)
        return job

    def get_job_status(self, job_id: str) -> Optional[ETLJob]:
        return next((j for j in self.jobs if j.job_id == job_id), None)

    def get_job_history(self, limit: int = 100) -> List[ETLJob]:
        return self.jobs[-limit:]
