"""
Simple database models used for authentication

Based mostly on Flask-Security tutorial:
https://pythonhosted.org/Flask-Security/quickstart.html

These are kept separate from the workflow tables (eg. no relations between
authentication tables and the workflow tables). If we wanted to add relations,
(eg. who enqueued which object), it would be better to move these models
into `passari-workflow` to keep migrations under one repository.
"""
from flask_security import RoleMixin, UserMixin
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship

from passari_web_ui.db import db

Base = declarative_base()
Base.query = db.session.query_property()


class RolesUsers(Base):
    __tablename__ = 'roles_users'

    id = Column(Integer(), primary_key=True)
    user_id = Column('user_id', Integer(), ForeignKey('user.id'))
    role_id = Column('role_id', Integer(), ForeignKey('role.id'))


class Role(Base, RoleMixin):
    __tablename__ = 'role'

    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))


class User(Base, UserMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    username = Column(String(255))
    password = Column(String(255))
    last_login_at = Column(DateTime())
    current_login_at = Column(DateTime())
    last_login_ip = Column(String(100))
    current_login_ip = Column(String(100))
    login_count = Column(Integer)
    active = Column(Boolean())
    confirmed_at = Column(DateTime())
    roles = relationship('Role', secondary='roles_users',
                         backref=backref('users', lazy='dynamic'))
