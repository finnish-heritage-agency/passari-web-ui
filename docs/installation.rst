Installation
============

Follow the installation instructions for *Passari* and *Passari Workflow* and ensure both are installed in the same virtualenv and configured. Once that is done, you can continue by installing *Passari Web UI*:

.. code-block:: console

   $ pip install passari-web-ui

Create the database tables for the web UI using the following command:

.. code-block:: console

   $ flask create-db

This should also create the configuration file `~/.config/passari-web-ui/config.toml` if it does not exist already. You can copy this file to `/etc/passari-web-ui/config.toml`, in which case it will take precedence over the user-specific configuration file.

.. code-block::

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
   # {MUSEUMPLUS_UI_URL}/object/1522
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

After you have configured the web UI, you need to create at least one account to access it:

.. code-block:: console

   $ flask users create --password <password> -a <email>

You can now run the included `run.sh` script to test the web UI:

.. code-block:: console

   $ ./run.sh

.. warning::

   The included `run.sh` script is only included for testing the application. Do not use it in production.
