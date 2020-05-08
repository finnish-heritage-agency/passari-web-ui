import click
from flask.cli import with_appcontext

from passari_web_ui.db.models import Base
from passari_web_ui.db import db


@click.command(help="Create web UI database tables")
@with_appcontext
def create_db():
    """
    Create web UI authentication database tables
    """
    print("Creating tables...")
    Base.metadata.create_all(db.engine)
    print("Done")
