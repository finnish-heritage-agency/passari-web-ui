Deployment
==========

*Passari Web UI* is built using the `Flask <https://flask.palletsprojects.com/>`_ framework and it is deployed using the Python's `WSGI <https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface>`_ protocol.

For example, you can use *nginx* and *uWSGI* to deploy the application on one of the worker servers as described in the documentation for *Passari Workflow*. More details can also be found in the uWSGI documentation `here <https://uwsgi-docs.readthedocs.io/en/latest/tutorials/Django_and_nginx.html>`_.

.. warning::

   When deploying the application, ensure that the application is deployed using the same user as the workflow.

An example of a configuration for uWSGI:

.. code-block::

   [uwsgi]
   chdir = /home/passari/passari-web-ui
   module = passari_web_ui.wsgi
   home = /home/passari/passari-venv

   master = true
   plugins = python36
   processes = 2
   socket = /var/uwsgi/passari_web_ui.sock

   uid = passari
   gid = passari

   chmod-socket = 660
   chown-socket = passari:nginx
   vacuum = true

   touch-reload = /tmp/passari-web-ui-reload

   stats = /tmp/passari-web-ui-stats.sock
