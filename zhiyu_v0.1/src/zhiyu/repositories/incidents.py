from sqlalchemy import select
from sqlalchemy.orm import Session

from zhiyu.db.models import IncidentRow


class IncidentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, incident_id: str, environment_ids: frozenset[str]) -> IncidentRow | None:
        return self.db.scalar(
            select(IncidentRow).where(
                IncidentRow.incident_id == incident_id,
                IncidentRow.environment_id.in_(environment_ids),
            )
        )
