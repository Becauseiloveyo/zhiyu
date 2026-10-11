from sqlalchemy import update

from zhiyu.core.errors import StaleVersionError
from zhiyu.db.mapping import values_for
from zhiyu.db.models import ResourceRow
from zhiyu.domain.contracts import ResourceRef
from zhiyu.repositories.base import BootstrapRepository


class ResourceRepository(BootstrapRepository[ResourceRow, ResourceRef]):
    row_type = ResourceRow
    contract_type = ResourceRef

    def replace_binding(self, resource: ResourceRef, *, expected_version: int) -> None:
        """Explicit CAS; caller must audit and commit in the same transaction."""
        values = values_for(resource, ResourceRow)
        updated = self.db.execute(
            update(ResourceRow)
            .where(
                ResourceRow.environment_id == resource.environment_id,
                ResourceRow.resource_id == resource.resource_id,
                ResourceRow.row_version == expected_version,
                ResourceRow.binding_version < resource.binding_version,
            )
            .values(**values, row_version=expected_version + 1)
            .returning(ResourceRow.resource_id)
        ).scalar_one_or_none()
        if updated is None:
            raise StaleVersionError("binding update requires current row version and a newer binding version")
