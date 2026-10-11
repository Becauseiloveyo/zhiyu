"""Explicit contract-to-row registry for consistency checks and conversion."""

from zhiyu.db import models
from zhiyu.db.base import Base
from zhiyu.domain import contracts

CONTRACT_ROWS: dict[type[contracts.Contract], type[Base]] = {
    contracts.EnvironmentProfile: models.EnvironmentRow,
    contracts.ResourceRef: models.ResourceRow,
    contracts.ScopeDefinition: models.ScopeRow,
    contracts.NormalizedEvent: models.EventRow,
    contracts.EventGroup: models.EventGroupRow,
    contracts.CorrelationDecision: models.CorrelationDecisionRow,
    contracts.Evidence: models.EvidenceRow,
    contracts.SensorHealth: models.SensorHealthRow,
    contracts.StateEntity: models.StateEntityRow,
    contracts.StateRelation: models.StateRelationRow,
    contracts.SecurityIncident: models.IncidentRow,
    contracts.ContextBundle: models.ContextRow,
    contracts.WorkerLease: models.WorkerLeaseRow,
    contracts.Task: models.TaskRow,
    contracts.AIPlan: models.PlanRow,
    contracts.ModelRun: models.ModelRunRow,
    contracts.CapabilityManifest: models.CapabilityRow,
    contracts.CapabilityHealth: models.CapabilityHealthRow,
    contracts.ActionRequest: models.ActionRow,
    contracts.ApprovalRecord: models.ApprovalRow,
    contracts.AuthorizationContext: models.AuthorizationContextRow,
    contracts.AuthorizationDecision: models.AuthorizationDecisionRow,
    contracts.ActionAttempt: models.ActionAttemptRow,
    contracts.VerificationSpec: models.VerificationSpecRow,
    contracts.VerificationResult: models.VerificationResultRow,
    contracts.ValidationScenario: models.ValidationScenarioRow,
    contracts.ValidationRun: models.ValidationRunRow,
    contracts.PolicySnapshot: models.PolicySnapshotRow,
    contracts.AuditEntry: models.AuditEntryRow,
    contracts.OutboxMessage: models.OutboxRow,
}
