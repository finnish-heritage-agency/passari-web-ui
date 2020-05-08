from setuptools import setup, find_packages


DESCRIPTION = (
    "Web interface for Passari workflow"
)
LONG_DESCRIPTION = DESCRIPTION
AUTHOR = "Janne Pulkkinen"
AUTHOR_EMAIL = "janne.pulkkinen@museovirasto.fi"


setup(
    name="passari_web_ui",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    packages=find_packages("src"),
    include_package_data=True,
    package_dir={"passari_web_ui": "src/passari_web_ui"},
    install_requires=[
        "Flask", "Flask-Security-Too", "click", "SQLAlchemy", "psycopg2",
        "rq", "rq-dashboard", "toml", "bcrypt", "Flask-SQLAlchemy",
        "Flask-WTF", "flask-talisman", "arrow"
    ],
    use_scm_version=True,
    setup_requires=["setuptools_scm"]
)
