import datetime
import os
import subprocess
from pathlib import Path

from flask_security import SQLAlchemySessionUserDatastore, hash_password
from sqlalchemy import create_engine

import fakeredis
import pytest
from passari_web_ui.app import create_app
from passari_web_ui.db import db
from passari_web_ui.db.models import Base as AuthBase
from passari_web_ui.db.models import Role, User
from passari_workflow.config import CONFIG as WORKFLOW_CONFIG
from passari_workflow.db import DBSession
from passari_workflow.db.connection import connect_db
from passari_workflow.db.models import Base, MuseumObject, MuseumPackage
from pytest_postgresql.janitor import DatabaseJanitor


@pytest.fixture(scope="function", autouse=True)
def redis(monkeypatch):
    """
    Fixture for a fake Redis server
    """
    server = fakeredis.FakeServer()
    conn = fakeredis.FakeStrictRedis(server=server)

    monkeypatch.setattr(
        "passari_workflow.queue.queues.get_redis_connection",
        lambda: conn
    )
    monkeypatch.setattr(
        "passari_web_ui.api.views.get_redis_connection",
        lambda: conn
    )
    monkeypatch.setattr(
        "passari_workflow.heartbeat.get_redis_connection",
        lambda: conn
    )

    yield conn


@pytest.fixture(scope="session")
def database(request):
    """
    Fixture for starting an ephemeral database instance for the duration
    of the test suite
    """
    def get_psql_version():
        result = subprocess.check_output(["psql", "--version"]).decode("utf-8")
        version = result.split(" ")[-1].strip()
        major, minor, *_ = version.split(".")

        # Get the major and minor version, which are what pytest-postgresql
        # wants
        return f"{major}.{minor}"

    if os.environ.get("POSTGRES_USER"):
        # Use separately launched process if environments variables are defined
        # This is used in Gitlab CI tests which run in a Docker container
        user = os.environ["POSTGRES_USER"]
        host = os.environ["POSTGRES_HOST"]
        password = os.environ["POSTGRES_PASSWORD"]

        # POSTGRES_PORT can also be a value such as "tcp://1.1.1.1:5432"
        # This handles that format as well
        port = int(os.environ.get("POSTGRES_PORT", "5432").split(":")[-1])
        db_name = "passari_test"
        version = os.environ["POSTGRES_VERSION"]
        create_engine(
            f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        )

        yield request.getfixturevalue("postgresql_nooproc")
    else:
        # Launch PostgreSQL ourselves
        postgresql = request.getfixturevalue("postgresql_proc")

        user = postgresql.user
        host = postgresql.host
        port = postgresql.port
        db_name = "passari_test"

        version = get_psql_version()

        with DatabaseJanitor(user, host, port, db_name, version):
            create_engine(
                f"postgresql://{user}@{host}:{port}/{db_name}"
            )
            yield postgresql


@pytest.fixture(scope="function")
def engine(database, monkeypatch):
    """
    Fixture for creating an empty database on each test run
    """
    monkeypatch.setitem(WORKFLOW_CONFIG["db"], "user", database.user)
    monkeypatch.setitem(
        WORKFLOW_CONFIG["db"], "password",
        # Password authentication is used when running tests using Docker
        os.environ.get("POSTGRES_PASSWORD", "")
    )
    monkeypatch.setitem(WORKFLOW_CONFIG["db"], "host", database.host)
    monkeypatch.setitem(WORKFLOW_CONFIG["db"], "port", database.port)
    monkeypatch.setitem(WORKFLOW_CONFIG["db"], "name", "passari_test")

    engine = connect_db()

    # pg_trgm extension must exist
    engine.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    Base.metadata.create_all(engine)
    AuthBase.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    AuthBase.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(engine, database):
    """
    Fixture for a database session object for running database queries
    in test functions
    """
    conn = engine.connect()
    session = DBSession(bind=conn)

    yield session

    session.close()
    conn.close()


@pytest.fixture(scope="function")
def app(session, database, engine):
    """
    Test web application fixture
    """
    app = create_app()
    app.config["DEBUG"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = engine.url
    app.config["WTF_CSRF_ENABLED"] = False

    yield app


@pytest.fixture(scope="function")
def client(app):
    """
    Test web application client fixture for making requests
    """
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def user(app, client):
    """
    Fixture for an active logged-in user
    """
    with app.app_context():
        user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role)
        user = user_datastore.create_user(
            email="test@test.com", password=hash_password("testpassword")
        )
        user_datastore.activate_user(user)

        client.post(
            "/web-ui/login",
            data={"email": "test@test.com", "password": "testpassword"},
            follow_redirects=True
        )

    yield user


PLACEHOLDER_DATE = datetime.datetime(
    2019, 1, 2, 10, 0, 0, 0, tzinfo=datetime.timezone.utc
)


@pytest.fixture(scope="function")
def museum_object_factory(session):
    """
    Factory fixture for creating MuseumObject entries
    """
    def func(**kwargs):
        if "created_date" not in kwargs:
            kwargs["created_date"] = PLACEHOLDER_DATE
        if "modified_date" not in kwargs:
            kwargs["modified_date"] = PLACEHOLDER_DATE

        museum_object = MuseumObject(**kwargs)
        session.add(museum_object)
        session.commit()

        return museum_object

    return func


@pytest.fixture(scope="function")
def museum_package_factory(session):
    """
    Factory fixture for creating MuseumPackage entries
    """
    def func(**kwargs):
        museum_package = MuseumPackage(**kwargs)
        session.add(museum_package)
        session.commit()

        return museum_package

    return func
