from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class AgentMetadata:
    name: str
    version: str
    model_type: str
    provider: str
    capabilities: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    author: str = ""
    license: str = "MIT"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "model_type": self.model_type,
            "provider": self.provider,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "configuration": self.configuration,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "description": self.description,
            "author": self.author,
            "license": self.license,
        }
