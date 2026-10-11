"""Immutable effectiveness interpretation."""

from alembic import op

revision = "0009_decisions"
down_revision = "0008_verification"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE verification_effectiveness (\n\tverification_id TEXT NOT NULL, \n\traw_dimensions JSONB NOT NULL, \n\tqualification_failures JSONB NOT NULL, \n\tdecision JSONB NOT NULL, \n\tdecided_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdecision_ms FLOAT NOT NULL, \n\tCONSTRAINT pk_verification_effectiveness PRIMARY KEY (verification_id), \n\tCONSTRAINT fk_verification_effectiveness_verification_id_verificat_50be FOREIGN KEY(verification_id) REFERENCES verification_results (verification_id)\n)\n\n"
    )
    op.execute(
        "CREATE TRIGGER immutable_verification_effectiveness BEFORE UPDATE OR DELETE ON verification_effectiveness FOR EACH ROW EXECUTE FUNCTION zhiyu_reject_mutation()"
    )


def downgrade():
    op.drop_table("verification_effectiveness")
