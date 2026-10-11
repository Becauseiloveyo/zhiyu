"""Safe error classes; never return database statements or event contents to callers."""


class DomainError(ValueError):
    code = "invalid_request"


class ConflictError(DomainError):
    code = "identity_conflict"


class ReferenceError(DomainError):
    code = "invalid_reference"


class AccessDenied(DomainError):
    code = "access_denied"


class StaleVersionError(ConflictError):
    code = "stale_version"


class LeaseLostError(ConflictError):
    code = "lease_lost"
