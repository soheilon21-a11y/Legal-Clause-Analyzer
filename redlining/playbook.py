"""Playbook loading and discovery.

Reads JSON playbook files from the ``playbooks/`` directory and
returns validated ``Playbook`` instances. New playbooks are picked up
automatically — just drop a ``.json`` file into the directory.
"""

import json
from pathlib import Path

from redlining.models import Playbook

PLAYBOOKS_DIR = Path("playbooks")


def load_playbook(path: Path) -> Playbook:
    """Load and validate a single playbook from a JSON file.

    Args:
        path: Path to a ``.json`` playbook file.

    Returns:
        A validated ``Playbook`` instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is malformed or fails validation.
    """
    if not path.exists():
        raise FileNotFoundError(f"Playbook not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    return Playbook(**raw)


def load_playbook_by_id(
    playbook_id: str,
    directory: Path = PLAYBOOKS_DIR,
) -> Playbook:
    """Find and load a playbook by its unique ID.

    Scans all ``.json`` files in ``directory`` and returns the first
    playbook whose ``playbook_id`` matches.

    Args:
        playbook_id: The unique playbook identifier to search for.
        directory: Directory to scan. Defaults to ``playbooks/``.

    Returns:
        The matching ``Playbook``.

    Raises:
        FileNotFoundError: If no playbook with the given ID exists.
    """
    for playbook in load_all_playbooks(directory):
        if playbook.playbook_id == playbook_id:
            return playbook

    raise FileNotFoundError(
        f"No playbook with id '{playbook_id}' found in '{directory}'."
    )


def load_all_playbooks(directory: Path = PLAYBOOKS_DIR) -> list[Playbook]:
    """Load every valid ``.json`` playbook from ``directory``.

    Files that fail validation are silently skipped so a single
    corrupt file does not block the entire engine.

    Args:
        directory: Directory to scan. Defaults to ``playbooks/``.

    Returns:
        A list of validated ``Playbook`` instances, sorted by filename.
    """
    if not directory.exists():
        return []

    playbooks: list[Playbook] = []

    for path in sorted(directory.glob("*.json")):
        try:
            playbooks.append(load_playbook(path))
        except (json.JSONDecodeError, ValueError):
            continue

    return playbooks
