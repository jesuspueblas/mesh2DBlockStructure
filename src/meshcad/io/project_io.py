"""Save and load projects in JSON format (plain dictionaries).

This module does not depend on the GUI: it accepts and returns dictionaries.
Conversion between dictionaries and Document objects belongs to the GUI
layer, which is the only layer that knows about Qt. This allows
`meshcad.io` to be imported without PyQt5 installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def save_project(data: Dict[str, Any], path) -> None:
    """Write a serialized project to disk as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_project(path) -> Dict[str, Any]:
    """Read a project from disk and return its dictionary."""
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))
