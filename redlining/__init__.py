"""Redlining engine for AI-assisted contract negotiation.

Provides clause detection against legal playbooks, alternative wording
suggestions, and professional redline report generation. The engine
never modifies contracts automatically — all suggestions require
lawyer approval.
"""

from redlining.models import (
    PlaybookRule,
    Playbook,
    RedlineSuggestion,
    RedlineRequest,
    RedlineResult,
)
from redlining.playbook import load_playbook, load_all_playbooks
from redlining.engine import RedliningEngine

__all__ = [
    "PlaybookRule",
    "Playbook",
    "RedlineSuggestion",
    "RedlineRequest",
    "RedlineResult",
    "load_playbook",
    "load_all_playbooks",
    "RedliningEngine",
]
