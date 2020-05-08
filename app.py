import sys
from pathlib import Path


# Manipulate sys.path to find the modules inside 'src/passari_web_ui'
sys.path.insert(
    1, str(Path(__file__).resolve().parent / "src")
)

from passari_web_ui.app import create_app

app = create_app()
