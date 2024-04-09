"""Init alter.

Revision ID: 0002
Revises: 0001
Create Date: 2024-04-09 14:48:14.415826

"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Apply migrations to database."""
    op.create_foreign_key(
        None,
        "related_model",
        "test_model",
        ["test_model_id"],
        ["id"],
        ondelete="CASCADE",
        use_alter=True,
    )


def downgrade() -> None:
    """Roll back migrations from database."""
    op.drop_constraint(
        "related_model_test_model_id_fkey",
        "related_model",
        type_="foreignkey",
    )
