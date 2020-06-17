import os
from pathlib import Path

import click
import toml


DEFAULT_CONFIG = """
[flask]
# Replace this with a secure randomly generated string in production
SECRET_KEY='test secret key DO NOT USE'
SECURITY_URL_PREFIX='/web-ui/'
# Replace this with a random string in production
SECURITY_PASSWORD_SALT='replace with random string'
SECURITY_SEND_REGISTER_EMAIL=false
SECURITY_SEND_PASSWORD_CHANGE_EMAIL=false
SECURITY_SEND_PASSWORD_RESET_EMAIL=false
SECURITY_SEND_PASSWORD_RESET_NOTICE_EMAIL=false

# URL to the MuseumPlus web UI. This is the base URL.
# For example, the following URL should be valid:
# {MUSEUMPLUS_UI_URL}/Object/1522
MUSEUMPLUS_UI_URL=''

# The expected heartbeat intervals for automated procedures plus an
# additional period to account for small delays.
# If the most recent heartbeat for a procedure is older, a warning
# will be displayed in the UI.
# 1 hour (expected) + 15 minutes
HEARTBEAT_INTERVAL_SYNC_PROCESSED_SIPS=4500
# 48 hours (expected) + 1 hour
HEARTBEAT_INTERVAL_SYNC_OBJECTS=176400
# 48 hours (expected) + 1 hour
HEARTBEAT_INTERVAL_SYNC_ATTACHMENTS=176400
# 24 hours (expected) + 1 hour
HEARTBEAT_INTERVAL_SYNC_HASHES=90000
"""[1:]


def get_config(app_name, config_name, default_config):
    """
    Try retrieving the configuration file content from the following sources
    in the following order:
    1. <APP_NAME>_CONFIG_PATH env var, if provided
    2. '/etc/<app_name>/<config_name>' path
    3. Local configuration directory as determined by `click.get_app_dir()`

    In addition, the default config will be written to source 3 in case no
    config sources are available.
    """
    env_name = f"{app_name.upper().replace('-', '_')}_CONFIG_PATH"
    if os.environ.get(env_name):
        return Path(os.environ[env_name]).read_text()

    system_path = Path("/etc") / app_name / config_name
    if system_path.is_file():
        return system_path.read_text()

    local_path = Path(click.get_app_dir(app_name)) / config_name
    if local_path.is_file():
        return local_path.read_text()

    local_path.parent.mkdir(exist_ok=True)
    local_path.write_text(default_config)
    return default_config


def get_flask_config():
    config = get_config("passari-web-ui", "config.toml", DEFAULT_CONFIG)
    return toml.loads(config)["flask"]
