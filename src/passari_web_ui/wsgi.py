"""
WSGI module used for deploying the application
"""
from passari_web_ui.app import create_app

application = create_app()
