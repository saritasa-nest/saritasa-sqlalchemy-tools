import invoke
import saritasa_invocations

import invocations

ns = invoke.Collection(  # type: ignore
    invocations.project,
    saritasa_invocations.docker,
    saritasa_invocations.git,
    saritasa_invocations.github_actions,
    saritasa_invocations.pre_commit,
    saritasa_invocations.python,
    saritasa_invocations.system,
    saritasa_invocations.poetry,
    saritasa_invocations.mypy,
    saritasa_invocations.pytest,
    saritasa_invocations.alembic,
)

# Configurations for run command
ns.configure(
    {
        "run": {
            "pty": True,
            "echo": True,
        },
        "saritasa_invocations": saritasa_invocations.Config(
            project_name="saritasa-sqlalchemy-tools",
            docker=saritasa_invocations.DockerSettings(
                main_containers=("postgres",),
            ),
            alembic=saritasa_invocations.AlembicSettings(
                migrations_folder="tests/alembic/versions",
            ),
        ),
    },
)
