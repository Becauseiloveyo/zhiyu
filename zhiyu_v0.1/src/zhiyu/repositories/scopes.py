from zhiyu.db.infrastructure import ScopeResourceRow
from zhiyu.db.models import ScopeRow
from zhiyu.domain.contracts import ScopeDefinition
from zhiyu.repositories.base import BootstrapRepository


class ScopeRepository(BootstrapRepository[ScopeRow, ScopeDefinition]):
    row_type = ScopeRow
    contract_type = ScopeDefinition

    def create(self, contract: ScopeDefinition) -> bool:
        created = super().create(contract)
        if created:
            for role, resources in (
                ("SOURCE", contract.source_resource_ids),
                ("TARGET", contract.target_resource_ids),
            ):
                for resource_id in sorted(set(resources)):
                    self.db.add(
                        ScopeResourceRow(
                            environment_id=contract.environment_id,
                            scope_id=contract.scope_id,
                            resource_id=resource_id,
                            role=role,
                        )
                    )
            self.db.flush()
        return created
