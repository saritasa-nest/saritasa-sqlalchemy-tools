import pytest

import sqlalchemy

import saritasa_sqlalchemy_tools


@pytest.fixture
def generated_enum() -> type[saritasa_sqlalchemy_tools.OrderingEnum]:
    """Generate enum for testing."""
    return saritasa_sqlalchemy_tools.OrderingEnum(  # type: ignore
        "GeneratedEnum",
        [
            "field",
        ],
    )


def test_ordering_enum_generated_values(
    generated_enum: type[saritasa_sqlalchemy_tools.OrderingEnum],
) -> None:
    """Test ordering enum generation.

    Check that reverse option are present.

    """
    assert hasattr(generated_enum, "field")
    assert generated_enum.field == "field"
    assert hasattr(generated_enum, "field_desc")
    assert generated_enum.field_desc == "-field"


def test_ordering_enum_generated_sql_clause(
    generated_enum: type[saritasa_sqlalchemy_tools.OrderingEnum],
) -> None:
    """Test that ordering enum generates correct sql clause."""
    assert generated_enum.field.sql_clause == "field"
    expected_db_clause: sqlalchemy.UnaryExpression[str] = sqlalchemy.desc(
        "field",
    )
    actual_db_clause = generated_enum.field_desc.sql_clause
    assert actual_db_clause.__class__ == expected_db_clause.__class__
    assert actual_db_clause.modifier == expected_db_clause.modifier
    assert actual_db_clause.operator == expected_db_clause.operator
