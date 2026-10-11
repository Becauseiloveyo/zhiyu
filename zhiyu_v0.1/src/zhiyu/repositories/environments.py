from zhiyu.db.models import EnvironmentRow
from zhiyu.domain.contracts import EnvironmentProfile
from zhiyu.repositories.base import BootstrapRepository


class EnvironmentRepository(BootstrapRepository[EnvironmentRow, EnvironmentProfile]):
    row_type = EnvironmentRow
    contract_type = EnvironmentProfile
