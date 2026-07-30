"""Unit tests for ``redlining.engine.RedliningEngine``.

Tests every public and private method of the engine using synthetic
playbooks and contract texts. LLM calls are mocked so the suite
runs without a local model server.
"""

from unittest.mock import MagicMock, patch

import pytest

from redlining.engine import RedliningEngine
from redlining.models import (
    Playbook,
    PlaybookRule,
    RedlineRequest,
    RedlineSuggestion,
)


def _rule(
    clause_type: str = "Test Clause",
    keywords: list[str] | None = None,
    negotiable: bool = True,
    risk_level: str = "Medium",
) -> PlaybookRule:
    return PlaybookRule(
        clause_type=clause_type,
        detection_keywords=keywords or ["test keyword"],
        preferred_wording=f"Preferred wording for {clause_type}.",
        reason=f"Reason for {clause_type}.",
        risk_level=risk_level,
        negotiable=negotiable,
    )


def _playbook(
    pb_id: str = "test_pb",
    rules: list[PlaybookRule] | None = None,
) -> Playbook:
    return Playbook(
        playbook_id=pb_id,
        playbook_name=f"Playbook {pb_id}",
        jurisdiction="Test",
        rules=rules or [_rule()],
    )


CONTRACT_WITH_KEYWORDS = (
    "This agreement contains a limitation of liability provision "
    "capping all liability. Either party may terminate this agreement "
    "with thirty days written notice. Both parties must protect "
    "confidential information at all times."
)

CONTRACT_WITHOUT_KEYWORDS = (
    "This agreement sets out general cooperation between the two "
    "companies regarding quarterly planning and shared logistics."
)


class TestExtractClauseContext:
    def test_returns_context_around_keyword(self) -> None:
        engine = RedliningEngine(playbooks=[])
        text = "AAA. " * 100 + "limitation of liability applies. " + "BBB. " * 100
        ctx = engine._extract_clause_context(text, "limitation of liability")
        assert "limitation of liability" in ctx.lower()

    def test_returns_prefix_when_keyword_missing(self) -> None:
        engine = RedliningEngine(playbooks=[])
        text = "Some contract text that does not contain the keyword."
        ctx = engine._extract_clause_context(text, "nonexistent")
        assert len(ctx) > 0

    def test_case_insensitive_match(self) -> None:
        engine = RedliningEngine(playbooks=[])
        text = "The LIMITATION OF LIABILITY clause is important."
        ctx = engine._extract_clause_context(text, "limitation of liability")
        assert "LIMITATION OF LIABILITY" in ctx


class TestMatchRule:
    def test_matches_when_keyword_present(self) -> None:
        engine = RedliningEngine(playbooks=[])
        rule = _rule(keywords=["terminate", "written notice"])
        matched, keywords = engine._match_rule(CONTRACT_WITH_KEYWORDS, rule)
        assert matched is True
        assert "terminate" in keywords

    def test_no_match_when_keyword_absent(self) -> None:
        engine = RedliningEngine(playbooks=[])
        rule = _rule(keywords=["force majeure", "act of god"])
        matched, keywords = engine._match_rule(CONTRACT_WITHOUT_KEYWORDS, rule)
        assert matched is False
        assert keywords == []

    def test_case_insensitive_matching(self) -> None:
        engine = RedliningEngine(playbooks=[])
        rule = _rule(keywords=["CONFIDENTIAL INFORMATION"])
        matched, _ = engine._match_rule(CONTRACT_WITH_KEYWORDS, rule)
        assert matched is True

    def test_multiple_keywords_all_matched(self) -> None:
        engine = RedliningEngine(playbooks=[])
        rule = _rule(keywords=["terminate", "confidential", "liability"])
        matched, keywords = engine._match_rule(CONTRACT_WITH_KEYWORDS, rule)
        assert matched is True
        assert len(keywords) == 3


class TestComputeConfidence:
    def test_zero_keywords_returns_zero(self) -> None:
        engine = RedliningEngine(playbooks=[])
        assert engine._compute_confidence([], 0, True) == 0.0

    def test_all_keywords_matched_high_confidence(self) -> None:
        engine = RedliningEngine(playbooks=[])
        score = engine._compute_confidence(["a", "b", "c"], 3, True)
        assert 0.8 <= score <= 0.95

    def test_non_negotiable_reduces_confidence(self) -> None:
        engine = RedliningEngine(playbooks=[])
        negotiable = engine._compute_confidence(["a", "b"], 3, True)
        non_negotiable = engine._compute_confidence(["a", "b"], 3, False)
        assert non_negotiable < negotiable

    def test_partial_match_moderate_confidence(self) -> None:
        engine = RedliningEngine(playbooks=[])
        score = engine._compute_confidence(["a"], 5, True)
        assert 0.5 <= score <= 0.8

    def test_score_capped_at_0_95(self) -> None:
        engine = RedliningEngine(playbooks=[])
        score = engine._compute_confidence(["a"] * 100, 1, True)
        assert score <= 0.95


class TestSelectPlaybooks:
    def test_empty_ids_returns_all(self) -> None:
        pb1 = _playbook("pb1")
        pb2 = _playbook("pb2")
        engine = RedliningEngine(playbooks=[pb1, pb2])
        selected = engine._select_playbooks([])
        assert len(selected) == 2

    def test_valid_ids_filters(self) -> None:
        pb1 = _playbook("pb1")
        pb2 = _playbook("pb2")
        engine = RedliningEngine(playbooks=[pb1, pb2])
        selected = engine._select_playbooks(["pb1"])
        assert len(selected) == 1
        assert selected[0].playbook_id == "pb1"

    def test_invalid_ids_ignored(self) -> None:
        pb1 = _playbook("pb1")
        engine = RedliningEngine(playbooks=[pb1])
        selected = engine._select_playbooks(["nonexistent"])
        assert selected == []

    def test_mixed_valid_and_invalid_ids(self) -> None:
        pb1 = _playbook("pb1")
        pb2 = _playbook("pb2")
        engine = RedliningEngine(playbooks=[pb1, pb2])
        selected = engine._select_playbooks(["pb1", "ghost"])
        assert len(selected) == 1


class TestGenerateSuggestion:
    def test_produces_correct_structure(self) -> None:
        pb = _playbook()
        rule = _rule(keywords=["terminate"])
        engine = RedliningEngine(playbooks=[pb])
        suggestion = engine._generate_suggestion(
            CONTRACT_WITH_KEYWORDS, rule, ["terminate"], pb
        )
        assert isinstance(suggestion, RedlineSuggestion)
        assert suggestion.clause_type == "Test Clause"
        assert suggestion.playbook_source == "test_pb"
        assert suggestion.jurisdiction == "Test"
        assert 0.0 <= suggestion.confidence_score <= 1.0
        assert suggestion.negotiable is True


class TestAnalyze:
    def test_detects_matching_negotiable_clauses(self) -> None:
        rules = [
            _rule("Termination", ["terminate", "written notice"], True, "Medium"),
            _rule("Confidentiality", ["confidential"], True, "High"),
        ]
        pb = _playbook(rules=rules)
        engine = RedliningEngine(playbooks=[pb])
        request = RedlineRequest(contract_text=CONTRACT_WITH_KEYWORDS)
        result = engine.analyze(request)

        clause_types = {s.clause_type for s in result.suggestions}
        assert "Termination" in clause_types
        assert "Confidentiality" in clause_types
        assert result.negotiable_clauses_found == len(result.suggestions)
        assert result.total_clauses_scanned == 2

    def test_no_suggestions_for_non_matching_text(self) -> None:
        rules = [_rule("Force Majeure", ["force majeure", "act of god"])]
        pb = _playbook(rules=rules)
        engine = RedliningEngine(playbooks=[pb])
        request = RedlineRequest(contract_text=CONTRACT_WITHOUT_KEYWORDS)
        result = engine.analyze(request)

        assert result.suggestions == []
        assert result.negotiable_clauses_found == 0

    def test_skips_non_negotiable_rules(self) -> None:
        rules = [
            _rule("Termination", ["terminate"], negotiable=False),
        ]
        pb = _playbook(rules=rules)
        engine = RedliningEngine(playbooks=[pb])
        request = RedlineRequest(contract_text=CONTRACT_WITH_KEYWORDS)
        result = engine.analyze(request)

        assert result.suggestions == []
        assert result.total_clauses_scanned == 1

    def test_deduplicates_clause_types(self) -> None:
        rules = [
            _rule("Termination", ["terminate"]),
            _rule("Termination", ["written notice"]),
        ]
        pb = _playbook(rules=rules)
        engine = RedliningEngine(playbooks=[pb])
        request = RedlineRequest(contract_text=CONTRACT_WITH_KEYWORDS)
        result = engine.analyze(request)

        termination_suggestions = [
            s for s in result.suggestions if s.clause_type == "Termination"
        ]
        assert len(termination_suggestions) == 1

    def test_sorts_by_risk_level(self) -> None:
        rules = [
            _rule("Low Clause", ["terminate"], True, "Low"),
            _rule("Critical Clause", ["confidential"], True, "Critical"),
            _rule("High Clause", ["liability"], True, "High"),
            _rule("Medium Clause", ["written notice"], True, "Medium"),
        ]
        pb = _playbook(rules=rules)
        engine = RedliningEngine(playbooks=[pb])
        request = RedlineRequest(contract_text=CONTRACT_WITH_KEYWORDS)
        result = engine.analyze(request)

        risk_order = [s.risk_level for s in result.suggestions]
        expected = sorted(
            risk_order,
            key=lambda r: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}.get(r, 4),
        )
        assert risk_order == expected

    def test_playbook_filter(self) -> None:
        pb1 = _playbook("pb1", [_rule("Termination", ["terminate"])])
        pb2 = _playbook("pb2", [_rule("Confidentiality", ["confidential"])])
        engine = RedliningEngine(playbooks=[pb1, pb2])
        request = RedlineRequest(
            contract_text=CONTRACT_WITH_KEYWORDS,
            playbook_ids=["pb1"],
        )
        result = engine.analyze(request)

        assert result.playbooks_used == ["pb1"]
        clause_types = {s.clause_type for s in result.suggestions}
        assert "Termination" in clause_types
        assert "Confidentiality" not in clause_types

    def test_playbooks_used_includes_all_selected(self) -> None:
        pb1 = _playbook("pb1")
        pb2 = _playbook("pb2")
        engine = RedliningEngine(playbooks=[pb1, pb2])
        request = RedlineRequest(contract_text=CONTRACT_WITHOUT_KEYWORDS)
        result = engine.analyze(request)

        assert set(result.playbooks_used) == {"pb1", "pb2"}

    def test_disclaimer_present(self) -> None:
        engine = RedliningEngine(playbooks=[_playbook()])
        request = RedlineRequest(contract_text=CONTRACT_WITHOUT_KEYWORDS)
        result = engine.analyze(request)
        assert "AI-assisted" in result.disclaimer


class TestLLMRefinement:
    def test_batch_refine_with_mock_llm(self) -> None:
        rules = [_rule("Termination", ["terminate"], True, "Medium")]
        pb = _playbook(rules=rules)
        engine = RedliningEngine(playbooks=[pb])

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='[{"clause_type": "Termination", "suggested_clause": "Improved termination clause."}]'
                )
            )
        ]

        with patch.object(engine, "_get_llm_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = (
                mock_response
            )
            request = RedlineRequest(
                contract_text=CONTRACT_WITH_KEYWORDS,
                use_llm=True,
            )
            result = engine.analyze(request)

        assert len(result.suggestions) == 1
        assert result.suggestions[0].suggested_clause == "Improved termination clause."

    def test_batch_refine_llm_failure_returns_original(self) -> None:
        rules = [_rule("Termination", ["terminate"], True, "Medium")]
        pb = _playbook(rules=rules)
        engine = RedliningEngine(playbooks=[pb])

        with patch.object(engine, "_get_llm_client") as mock_client:
            mock_client.return_value.chat.completions.create.side_effect = (
                RuntimeError("LLM unavailable")
            )
            request = RedlineRequest(
                contract_text=CONTRACT_WITH_KEYWORDS,
                use_llm=True,
            )
            result = engine.analyze(request)

        assert len(result.suggestions) == 1
        assert result.suggestions[0].suggested_clause == rules[0].preferred_wording

    def test_batch_refine_invalid_json_returns_original(self) -> None:
        rules = [_rule("Termination", ["terminate"], True, "Medium")]
        pb = _playbook(rules=rules)
        engine = RedliningEngine(playbooks=[pb])

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="not valid json at all"))
        ]

        with patch.object(engine, "_get_llm_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = (
                mock_response
            )
            request = RedlineRequest(
                contract_text=CONTRACT_WITH_KEYWORDS,
                use_llm=True,
            )
            result = engine.analyze(request)

        assert len(result.suggestions) == 1

    def test_no_llm_call_when_no_suggestions(self) -> None:
        rules = [_rule("Force Majeure", ["force majeure"])]
        pb = _playbook(rules=rules)
        engine = RedliningEngine(playbooks=[pb])

        with patch.object(engine, "_get_llm_client") as mock_client:
            request = RedlineRequest(
                contract_text=CONTRACT_WITHOUT_KEYWORDS,
                use_llm=True,
            )
            result = engine.analyze(request)
            mock_client.assert_not_called()

        assert result.suggestions == []


class TestEngineProperties:
    def test_playbooks_property_returns_copy(self) -> None:
        pb = _playbook()
        engine = RedliningEngine(playbooks=[pb])
        playbooks = engine.playbooks
        playbooks.clear()
        assert len(engine.playbooks) == 1

    def test_available_playbook_ids(self) -> None:
        pb1 = _playbook("alpha")
        pb2 = _playbook("beta")
        engine = RedliningEngine(playbooks=[pb1, pb2])
        assert engine.available_playbook_ids == ["alpha", "beta"]
