"""Init.

Revision ID: 0001
Revises:
Create Date: 2024-04-04 12:15:38.086722

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Apply migrations to database."""
    op.create_table(
        "related_model",
        sa.Column("test_model_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["test_model_id"],
            ["test_model.id"],
            ondelete="CASCADE",
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "soft_delete_test_model",
        sa.Column("text", sa.String(length=250), nullable=False),
        sa.Column("text_nullable", sa.String(length=30), nullable=True),
        sa.Column(
            "text_enum",
            sa.Enum("value_1", "value_2", "value_3", name="textenum"),
            nullable=False,
        ),
        sa.Column(
            "text_enum_nullable",
            sa.Enum("value_1", "value_2", "value_3", name="textenum"),
            nullable=True,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("number_nullable", sa.Integer(), nullable=True),
        sa.Column("small_number", sa.SmallInteger(), nullable=False),
        sa.Column("small_number_nullable", sa.SmallInteger(), nullable=True),
        sa.Column("decimal_number", sa.Numeric(), nullable=False),
        sa.Column("decimal_number_nullable", sa.Numeric(), nullable=True),
        sa.Column("boolean", sa.Boolean(), nullable=False),
        sa.Column("boolean_nullable", sa.Boolean(), nullable=True),
        sa.Column("text_list", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("text_list_nullable", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("date_time", sa.DateTime(), nullable=False),
        sa.Column("date_time_nullable", sa.DateTime(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("date_nullable", sa.Date(), nullable=True),
        sa.Column("timedelta", sa.Interval(), nullable=False),
        sa.Column("timedelta_nullable", sa.Interval(), nullable=True),
        sa.Column(
            "json_field",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "json_field_nullable",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deleted", sa.DateTime(), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_model",
        sa.Column("related_model_id", sa.Integer(), nullable=False),
        sa.Column("related_model_id_nullable", sa.Integer(), nullable=True),
        sa.Column("text", sa.String(length=250), nullable=False),
        sa.Column("text_nullable", sa.String(length=30), nullable=True),
        sa.Column(
            "text_enum",
            sa.Enum("value_1", "value_2", "value_3", name="textenum"),
            nullable=False,
        ),
        sa.Column(
            "text_enum_nullable",
            sa.Enum("value_1", "value_2", "value_3", name="textenum"),
            nullable=True,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("number_nullable", sa.Integer(), nullable=True),
        sa.Column("small_number", sa.SmallInteger(), nullable=False),
        sa.Column("small_number_nullable", sa.SmallInteger(), nullable=True),
        sa.Column("decimal_number", sa.Numeric(), nullable=False),
        sa.Column("decimal_number_nullable", sa.Numeric(), nullable=True),
        sa.Column("boolean", sa.Boolean(), nullable=False),
        sa.Column("boolean_nullable", sa.Boolean(), nullable=True),
        sa.Column("text_list", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("text_list_nullable", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("date_time", sa.DateTime(), nullable=False),
        sa.Column("date_time_nullable", sa.DateTime(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("date_nullable", sa.Date(), nullable=True),
        sa.Column("timedelta", sa.Interval(), nullable=False),
        sa.Column("timedelta_nullable", sa.Interval(), nullable=True),
        sa.Column(
            "json_field",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "json_field_nullable",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["related_model_id"],
            ["related_model.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["related_model_id_nullable"],
            ["related_model.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "m2m_model",
        sa.Column("test_model_id", sa.Integer(), nullable=False),
        sa.Column("related_model_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["related_model_id"],
            ["related_model.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["test_model_id"],
            ["test_model.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Roll back migrations from database."""
    op.drop_table("m2m_model")
    op.drop_table("test_model")
    op.drop_table("soft_delete_test_model")
    op.drop_table("related_model")
    op.execute("DROP TYPE textenum")