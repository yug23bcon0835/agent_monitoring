from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .agent_metadata import AgentMetadata


class AgentRegistry:
    def __init__(self):
        self.agents: Dict[str, AgentMetadata] = {}
        self.history: List[Dict[str, Any]] = []

    def register_agent(self, metadata: AgentMetadata) -> str:
        key = f"{metadata.name}:{metadata.version}"
        self.agents[key] = metadata
        self._log_action("register", key, metadata)
        return key

    def get_agent(self, name: str, version: str) -> Optional[AgentMetadata]:
        key = f"{name}:{version}"
        return self.agents.get(key)

    def list_agents(self, name: Optional[str] = None) -> List[AgentMetadata]:
        if name:
            return [m for k, m in self.agents.items() if k.startswith(f"{name}:")]
        return list(self.agents.values())

    def update_agent(self, name: str, version: str, updates: Dict[str, Any]) -> bool:
        key = f"{name}:{version}"
        if key not in self.agents:
            return False

        agent = self.agents[key]
        for field, value in updates.items():
            if hasattr(agent, field):
                setattr(agent, field, value)

        agent.updated_at = datetime.utcnow()
        self._log_action("update", key, updates)
        return True

    def delete_agent(self, name: str, version: str) -> bool:
        key = f"{name}:{version}"
        if key in self.agents:
            del self.agents[key]
            self._log_action("delete", key, {})
            return True
        return False

    def get_agent_history(self, name: str) -> List[Dict[str, Any]]:
        return [h for h in self.history if name in h.get("key", "")]

    def _log_action(self, action: str, key: str, data: Any):
        self.history.append({
            "action": action,
            "key": key,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        })

    def export_registry(self) -> Dict[str, Any]:
        return {
            "agents": {k: v.to_dict() for k, v in self.agents.items()},
            "history": self.history,
            "timestamp": datetime.utcnow().isoformat(),
        }
