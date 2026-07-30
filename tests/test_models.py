"""Tests for redlining Pydantic models.

Validates field constraints, defaults, and serialization behaviour
of every model in ``redlining.models``.
"""

import pytest
from pydantic import ValidationError

from redlining.models import (
    Playbook,
    PlaybookRule,
    RedlineRequest,
    RedlineResult,
    RedlineSuggestion,
)


def _make_rule(**overrides: object) -> PlaybookRule:
    defaults = {
        "clause_type": "Test Clause",
        "detection_keywords": ["test keyword"],
        "preferred_wording": "Replacement text.",
        "reason": "Test reason.",
    }
    defaults.update(overrides)
    return PlaybookRule(**defaults)


def _make_playbook(**overrides: object) -> Playbook:
    defaults = {
        "playbook_id": "test_pb",
        "playbook_name": "Test Playbook",
        "rules": [_make_rule()],
    }
    defaults.update(overrides)
    return Playbook(**defaults)


class TestPlaybookRule:
    def test_valid_rule_defaults(self) -> None:
        rule = _make_rule()
        assert rule.clause_type == "Test Clause"
        assert rule.negotiable is True
        assert rule.risk_level == "Medium"
        assert rule.alternative_wordings == []
        assert rule.jurisdiction_notes == ""

    def test_risk_level_accepts_all_valid_values(self) -> None:
        for level in ("Low", "Medium", "High", "Critical"):
            rule = _make_rule(risk_level=level)
            assert rule.risk_level == level

    def test_risk_level_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            _make_rule(risk_level="Extreme")

    def test_empty_detection_keywords_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_rule(detection_keywords=[])

    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            PlaybookRule(clause_type="X")


class TestPlaybook:
    def test_valid_playbook_defaults(self) -> None:
        pb = _make_playbook()
        assert pb.playbook_id == "test_pb"
        assert pb.jurisdiction == "General"
        assert pb.version == "1.0"
        assert len(pb.rules) == 1

    def test_empty_rules_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_playbook(rules=[])

    def test_multiple_rules(self) -> None:
        rules = [_make_rule(clause_type=f"Clause {i}") for i in range(5)]
        pb = _make_playbook(rules=rules)
        assert len(pb.rules) == 5


class TestRedlineSuggestion:
    def test_valid_suggestion(self) -> None:
        suggestion = RedlineSuggestion(
            clause_type="Termination",
            original_clause="Original text here.",
            suggested_clause="Better text here.",
            reason="Too vague.",
            risk_level="High",
            confidence_score=0.85,
        )
        assert suggestion.negotiable is True
        assert suggestion.playbook_source == ""
        assert suggestion.jurisdiction == "General"

    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RedlineSuggestion(
                clause_type="X",
                original_clause="orig",
                suggested_clause="sug",
                reason="r",
                risk_level="Low",
                confidence_score=-0.1,
            )

    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RedlineSuggestion(
                clause_type="X",
                original_clause="orig",
                suggested_clause="sug",
                reason="r",
                risk_level="Low",
                confidence_score=1.5,
            )

    def test_confidence_boundary_values(self) -> None:
        for score in (0.0, 1.0):
            s = RedlineSuggestion(
                clause_type="X",
                original_clause="orig",
                suggested_clause="sug",
                reason="r",
                risk_level="Low",
                confidence_score=score,
            )
            assert s.confidence_score == score


class TestRedlineRequest:
    def test_valid_request_defaults(self) -> None:
        req = RedlineRequest(contract_text="A" * 20)
        assert req.playbook_ids == []
        assert req.use_llm is False

    def test_short_text_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RedlineRequest(contract_text="short")

    def test_exact_min_length_accepted(self) -> None:
        req = RedlineRequest(contract_text="A" * 20)
        assert len(req.contract_text) == 20


class TestRedlineResult:
    def test_defaults(self) -> None:
        result = RedlineResult(
            total_clauses_scanned=10,
            negotiable_clauses_found=0,
        )
        assert result.suggestions == []
        assert result.playbooks_used == []
        assert "AI-assisted" in result.disclaimer

    def test_with_suggestions(self) -> None:
        suggestion = RedlineSuggestion(
            clause_type="Termination",
            original_clause="orig",
            suggested_clause="sug",
            reason="r",
            risk_level="Medium",
            confidence_score=0.7,
        )
        result = RedlineResult(
            suggestions=[suggestion],
            total_clauses_scanned=5,
            negotiable_clauses_found=1,
            playbooks_used=["pb1"],
        )
        assert len(result.suggestions) == 1
        assert result.playbooks_used == ["pb1"]

    def test_model_dump_round_trip(self) -> None:
        result = RedlineResult(
            total_clauses_scanned=3,
            negotiable_clauses_found=0,
        )
        data = result.model_dump()
        restored = RedlineResult(**data)
        assert restored == result
