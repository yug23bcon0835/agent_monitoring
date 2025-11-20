from typing import Dict, List, Optional
from datetime import datetime


class VersionManager:
    def __init__(self):
        self.versions: Dict[str, List[Dict]] = {}

    def create_version(self, agent_name: str, version: str, metadata: Dict) -> bool:
        if agent_name not in self.versions:
            self.versions[agent_name] = []

        self.versions[agent_name].append({
            "version": version,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        })
        return True

    def get_versions(self, agent_name: str) -> List[Dict]:
        return self.versions.get(agent_name, [])

    def get_latest_version(self, agent_name: str) -> Optional[Dict]:
        versions = self.get_versions(agent_name)
        return versions[-1] if versions else None

    def promote_version(self, agent_name: str, version: str, environment: str) -> bool:
        versions = self.get_versions(agent_name)
        for v in versions:
            if v["version"] == version:
                if "promotions" not in v:
                    v["promotions"] = []
                v["promotions"].append({
                    "environment": environment,
                    "promoted_at": datetime.utcnow().isoformat(),
                })
                return True
        return False

    def rollback_version(self, agent_name: str, target_version: str) -> bool:
        versions = self.get_versions(agent_name)
        for v in versions:
            if v["version"] == target_version:
                v["status"] = "active"
                v["rolled_back_at"] = datetime.utcnow().isoformat()
                return True
        return False
