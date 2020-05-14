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
        "Flask",
        "Flask-Security-Too",
        "click>=7", "click<8",
        "SQLAlchemy",
        "psycopg2",
        "rq>=1",
        "rq-dashboard>=0.6",
        "toml",
        "bcrypt",
        "Flask-SQLAlchemy",
        "Flask-WTF",
        "flask-talisman",
        "arrow"
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Framework :: Flask"
    ],
    python_requires=">=3.6",
    use_scm_version=True,
    setup_requires=["setuptools_scm"]
)
