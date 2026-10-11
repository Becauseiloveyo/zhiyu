from pydantic import BaseModel, ConfigDict, Field

from zhiyu.core.errors import AccessDenied


class ServicePrincipal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    principal_id: str = Field(min_length=1)
    environment_ids: frozenset[str]
    collector_ids: frozenset[str] = frozenset()
    source_types: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    # Configured by the operator: collectors forwarding one sensor share a provenance root.
    provenance_roots: dict[str, str] = Field(default_factory=dict)

    def require(self, permission: str, environment_id: str) -> None:
        if permission not in self.permissions or environment_id not in self.environment_ids:
            raise AccessDenied("principal cannot access requested environment or operation")
