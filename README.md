passari-web-ui
=====================

Web application to watch and administrate the workflow.

Installation
------------

```
sudo dnf install python3 python3-virtualenv
python3 -mvenv venv
source venv/bin/activate
# Install Passari first. Replace 1.0 with newer version if tagged.
pip install --upgrade git+https://github.com/finnish-heritage-agency/passari.git@1.0#egg=passari
# Install Passari Workflow 1.0. Replace 1.0 with newer version if tagged.
pip install --upgrade git+https://github.com/finnish-heritage-agency/passari-workflow.git@1.0#egg=passari-workflow
# Finally, install Passari Web UI 1.0. Replace 1.0 with newer version if tagged.
pip install --upgrade git+https://github.com/finnish-heritage-agency/passari-web-ui.git@1.0#egg=passari-web-ui
```

Documentation
-------------

Documentation can be generated using Sphinx by running the following command:

```
python setup.py build_sphinx
```
