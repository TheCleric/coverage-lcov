import os

import toml

__version__ = toml.load(os.path.join(os.path.dirname(__file__), "..", "pyproject.toml"))["tool"]["poetry"]["version"]