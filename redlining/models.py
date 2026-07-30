"""Pydantic models for the redlining engine.

Defines the data contracts for playbooks, redline suggestions, and
engine inputs/outputs. All models are immutable and hashable where
possible to prevent accidental mutation during processing.
"""

from typing import Literal
from pydantic import BaseModel, Field


class PlaybookRule(BaseModel):
    """A single clause-detection rule within a legal playbook.

    Each rule defines a clause type, the keywords that trigger detection,
    preferred alternative wording, and the risk level if the clause is
    found in its current form.
    """

    clause_type: str = Field(
        ...,
        description="Human-readable clause category name.",
    )
    detection_keywords: list[str] = Field(
        ...,
        min_length=1,
        description="Lowercase phrases that signal this clause type.",
    )
    negotiable: bool = Field(
        default=True,
        description="Whether this clause is typically negotiable.",
    )
    risk_level: Literal["Low", "Medium", "High", "Critical"] = Field(
        default="Medium",
        description="Risk level if the clause remains unchanged.",
    )
    preferred_wording: str = Field(
        ...,
        description="Recommended replacement text for the clause.",
    )
    alternative_wordings: list[str] = Field(
        default_factory=list,
        description="Fallback alternative phrasings.",
    )
    reason: str = Field(
        ...,
        description="Why this clause should be renegotiated.",
    )
    jurisdiction_notes: str = Field(
        default="",
        description="Jurisdiction-specific guidance or caveats.",
    )


class Playbook(BaseModel):
    """A legal playbook containing multiple clause rules.

    Playbooks are jurisdiction-aware collections of rules that define
    what clauses to flag and how to suggest improvements.
    """

    playbook_id: str = Field(
        ...,
        description="Unique identifier for this playbook.",
    )
    playbook_name: str = Field(
        ...,
        description="Human-readable playbook name.",
    )
    jurisdiction: str = Field(
        default="General",
        description="Target jurisdiction (e.g., 'EU', 'US', 'UK').",
    )
    version: str = Field(
        default="1.0",
        description="Playbook version string.",
    )
    rules: list[PlaybookRule] = Field(
        ...,
        min_length=1,
        description="Ordered list of clause-detection rules.",
    )


class RedlineSuggestion(BaseModel):
    """A single redline suggestion for lawyer review.

    Contains the original clause text, the suggested replacement,
    the reasoning, risk assessment, and a confidence score.
    """

    clause_type: str = Field(
        ...,
        description="The clause category this suggestion addresses.",
    )
    original_clause: str = Field(
        ...,
        description="The original clause text from the contract.",
    )
    suggested_clause: str = Field(
        ...,
        description="The proposed replacement wording.",
    )
    reason: str = Field(
        ...,
        description="Explanation of why this change is recommended.",
    )
    risk_level: Literal["Low", "Medium", "High", "Critical"] = Field(
        ...,
        description="Risk level if the clause remains unchanged.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Engine confidence in this suggestion (0.0 to 1.0).",
    )
    negotiable: bool = Field(
        default=True,
        description="Whether this clause is typically negotiable.",
    )
    playbook_source: str = Field(
        default="",
        description="ID of the playbook that generated this suggestion.",
    )
    jurisdiction: str = Field(
        default="General",
        description="Jurisdiction context for this suggestion.",
    )


class RedlineRequest(BaseModel):
    """Input payload for the redlining engine."""

    contract_text: str = Field(
        ...,
        min_length=20,
        description="Full or partial contract text to redline.",
    )
    playbook_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Specific playbook IDs to use. Empty list means all "
            "available playbooks."
        ),
    )
    use_llm: bool = Field(
        default=False,
        description="Use local LLM to refine wording suggestions.",
    )


class RedlineResult(BaseModel):
    """Output of the redlining engine."""

    suggestions: list[RedlineSuggestion] = Field(
        default_factory=list,
        description="Ordered list of redline suggestions.",
    )
    total_clauses_scanned: int = Field(
        ...,
        description="Total number of clause rules evaluated.",
    )
    negotiable_clauses_found: int = Field(
        ...,
        description="Number of negotiable clauses detected.",
    )
    playbooks_used: list[str] = Field(
        default_factory=list,
        description="IDs of playbooks applied during analysis.",
    )
    disclaimer: str = Field(
        default=(
            "These redline suggestions are AI-assisted and require "
            "lawyer review before use. They do not constitute legal advice."
        ),
        description="Mandatory disclaimer for all redline outputs.",
    )
