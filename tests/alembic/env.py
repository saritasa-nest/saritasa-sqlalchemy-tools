import saritasa_sqlalchemy_tools
import tests.models  # noqa

saritasa_sqlalchemy_tools.AlembicMigrations(
    target_metadata=saritasa_sqlalchemy_tools.models.BaseModel.metadata,
    db_driver="postgresql+asyncpg",
    db_user="saritasa-sqlalchemy-tools-user",
    db_password="manager",
    db_host="postgres",
    db_port=5432,
    db_name="saritasa-sqlalchemy-tools-dev",
    query={},  # type: ignore
).run()
