from typing import Dict, List, Optional
import logging
from datetime import datetime

from .database_manager import DatabaseManager


class SchemaManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.schema_version = "1.0"
        self.migrations: List[Dict[str, str]] = []

    def create_schema(self) -> bool:
        try:
            self.db_manager.create_tables()
            self.logger.info(f"Schema created (version {self.schema_version})")
            return True
        except Exception as e:
            self.logger.error(f"Error creating schema: {e}")
            return False

    def add_migration(self, version: str, description: str, sql: str):
        self.migrations.append({
            "version": version,
            "description": description,
            "sql": sql,
            "created_at": datetime.utcnow().isoformat(),
        })

    def list_migrations(self) -> List[Dict[str, str]]:
        return self.migrations

    def create_index(self, table_name: str, column_name: str) -> bool:
        try:
            session = self.db_manager.get_session()
            index_name = f"idx_{table_name}_{column_name}"
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name});"
            session.execute(sql)
            session.commit()
            self.logger.info(f"Index created: {index_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating index: {e}")
            return False
        finally:
            session.close()

    def get_schema_info(self) -> Dict[str, List[str]]:
        return {
            "version": self.schema_version,
            "tables": [
                "agents",
                "agent_executions",
                "metrics",
                "evaluation_runs",
                "alerts",
            ],
        }

    def export_schema(self, filepath: str) -> bool:
        try:
            import json

            schema_info = {
                "version": self.schema_version,
                "created_at": datetime.utcnow().isoformat(),
                "tables": self.get_schema_info()["tables"],
                "migrations": self.migrations,
            }

            with open(filepath, "w") as f:
                json.dump(schema_info, f, indent=2)

            self.logger.info(f"Schema exported to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting schema: {e}")
            return False
