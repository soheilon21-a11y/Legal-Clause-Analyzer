"""Core redlining engine.

Detects negotiable clauses in contract text, compares them against
loaded playbooks, and generates lawyer-reviewable redline suggestions.
The engine never modifies contracts automatically.
"""

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

from redlining.models import (
    Playbook,
    PlaybookRule,
    RedlineRequest,
    RedlineResult,
    RedlineSuggestion,
)
from redlining.playbook import load_all_playbooks
from redlining.prompts import (
    BATCH_REDLINE_USER_PROMPT,
    REDLINE_SYSTEM_PROMPT,
    REDLINE_USER_PROMPT,
)

logger = logging.getLogger(__name__)

LOCAL_LLM_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
MODEL_ID = os.environ.get("LLM_MODEL", "llama3")

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

_CLAUSE_CONTEXT_CHARS = 400

_RISK_SORT_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


class RedliningEngine:
    """Stateless engine that produces redline suggestions from contract text.

    The engine is designed to be instantiated once and reused across
    requests. Playbooks are loaded at construction time and cached.
    """

    def __init__(
        self,
        playbooks: list[Playbook] | None = None,
    ) -> None:
        self._playbooks = playbooks if playbooks is not None else load_all_playbooks()
        self._client: OpenAI | None = None

    @property
    def playbooks(self) -> list[Playbook]:
        return list(self._playbooks)

    @property
    def available_playbook_ids(self) -> list[str]:
        return [pb.playbook_id for pb in self._playbooks]

    def _get_llm_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=LOCAL_LLM_BASE_URL,
                api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            )
        return self._client

    def _select_playbooks(
        self,
        requested_ids: list[str],
    ) -> list[Playbook]:
        if not requested_ids:
            return list(self._playbooks)

        available = {pb.playbook_id: pb for pb in self._playbooks}
        return [
            available[pb_id]
            for pb_id in requested_ids
            if pb_id in available
        ]

    def _extract_clause_context(
        self,
        contract_text: str,
        matched_keyword: str,
    ) -> str:
        lower_text = contract_text.lower()
        lower_keyword = matched_keyword.lower()
        keyword_pos = lower_text.find(lower_keyword)

        if keyword_pos == -1:
            return contract_text[:_CLAUSE_CONTEXT_CHARS]

        start = max(0, keyword_pos - _CLAUSE_CONTEXT_CHARS // 2)
        end = min(len(contract_text), keyword_pos + _CLAUSE_CONTEXT_CHARS // 2)

        context = contract_text[start:end].strip()

        sentences = _SENTENCE_BOUNDARY.split(context)
        relevant: list[str] = []
        for sentence in sentences:
            if lower_keyword in sentence.lower():
                relevant.append(sentence)

        if relevant:
            return " ".join(relevant).strip()

        return context

    def _match_rule(
        self,
        contract_text: str,
        rule: PlaybookRule,
    ) -> tuple[bool, list[str]]:
        lower_text = contract_text.lower()
        matched = [
            kw for kw in rule.detection_keywords
            if kw.lower() in lower_text
        ]
        return (bool(matched), matched)

    def _compute_confidence(
        self,
        matched_keywords: list[str],
        total_keywords: int,
        negotiable: bool,
    ) -> float:
        if total_keywords == 0:
            return 0.0

        keyword_ratio = len(matched_keywords) / total_keywords
        base_confidence = min(0.6 + keyword_ratio * 0.3, 0.95)

        if not negotiable:
            base_confidence *= 0.8

        return round(base_confidence, 2)

    def _generate_suggestion(
        self,
        contract_text: str,
        rule: PlaybookRule,
        matched_keywords: list[str],
        playbook: Playbook,
    ) -> RedlineSuggestion:
        clause_context = self._extract_clause_context(
            contract_text,
            matched_keywords[0],
        )

        confidence = self._compute_confidence(
            matched_keywords,
            len(rule.detection_keywords),
            rule.negotiable,
        )

        return RedlineSuggestion(
            clause_type=rule.clause_type,
            original_clause=clause_context,
            suggested_clause=rule.preferred_wording,
            reason=rule.reason,
            risk_level=rule.risk_level,
            confidence_score=confidence,
            negotiable=rule.negotiable,
            playbook_source=playbook.playbook_id,
            jurisdiction=playbook.jurisdiction,
        )

    def _refine_with_llm(
        self,
        suggestion: RedlineSuggestion,
        rule: PlaybookRule,
    ) -> RedlineSuggestion:
        jurisdiction_section = ""
        if rule.jurisdiction_notes:
            jurisdiction_section = (
                f"Jurisdiction Notes: {rule.jurisdiction_notes}"
            )

        user_prompt = REDLINE_USER_PROMPT.format(
            clause_type=suggestion.clause_type,
            original_clause=suggestion.original_clause,
            risk_level=suggestion.risk_level,
            reason=suggestion.reason,
            preferred_wording=rule.preferred_wording,
            jurisdiction_section=jurisdiction_section,
        )

        try:
            client = self._get_llm_client()
            completion = client.chat.completions.create(
                model=MODEL_ID,
                messages=[
                    {"role": "system", "content": REDLINE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                top_p=0.9,
                max_tokens=500,
            )

            refined_text = (completion.choices[0].message.content or "").strip()

            if refined_text and len(refined_text) > 20:
                return suggestion.model_copy(
                    update={
                        "suggested_clause": refined_text,
                        "confidence_score": min(
                            suggestion.confidence_score + 0.05, 1.0
                        ),
                    }
                )

        except Exception as exc:
            logger.warning(
                "LLM refinement failed for '%s': %s",
                suggestion.clause_type,
                exc,
            )

        return suggestion

    def _refine_batch_with_llm(
        self,
        suggestions: list[RedlineSuggestion],
        rules_map: dict[str, PlaybookRule],
    ) -> list[RedlineSuggestion]:
        clauses_section = "\n\n".join(
            f"### Clause {i+1}: {s.clause_type}\n"
            f"Original: {s.original_clause}\n"
            f"Risk: {s.risk_level}\n"
            f"Reason: {s.reason}\n"
            f"Preferred: {rules_map[s.clause_type].preferred_wording}"
            for i, s in enumerate(suggestions)
        )

        user_prompt = BATCH_REDLINE_USER_PROMPT.format(
            clauses_section=clauses_section,
        )

        try:
            client = self._get_llm_client()
            completion = client.chat.completions.create(
                model=MODEL_ID,
                messages=[
                    {"role": "system", "content": REDLINE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                top_p=0.9,
                max_tokens=2000,
            )

            raw = (completion.choices[0].message.content or "").strip()

            json_start = raw.find("[")
            json_end = raw.rfind("]") + 1
            if json_start == -1 or json_end == 0:
                return suggestions

            parsed: list[dict[str, Any]] = json.loads(
                raw[json_start:json_end]
            )

            lookup = {item["clause_type"]: item["suggested_clause"]
                      for item in parsed if "clause_type" in item}

            refined: list[RedlineSuggestion] = []
            for suggestion in suggestions:
                if suggestion.clause_type in lookup:
                    refined.append(
                        suggestion.model_copy(
                            update={
                                "suggested_clause": lookup[suggestion.clause_type],
                                "confidence_score": min(
                                    suggestion.confidence_score + 0.05, 1.0
                                ),
                            }
                        )
                    )
                else:
                    refined.append(suggestion)

            return refined

        except Exception as exc:
            logger.warning("Batch LLM refinement failed: %s", exc)
            return suggestions

    def analyze(self, request: RedlineRequest) -> RedlineResult:
        """Run the full redlining analysis on contract text.

        Args:
            request: The redline request containing contract text and
                optional playbook filters.

        Returns:
            A ``RedlineResult`` with all suggestions and metadata.
        """
        selected_playbooks = self._select_playbooks(request.playbook_ids)
        contract_text = request.contract_text

        suggestions: list[RedlineSuggestion] = []
        seen_clause_types: set[str] = set()
        rules_map: dict[str, PlaybookRule] = {}
        total_rules_scanned = 0

        for playbook in selected_playbooks:
            for rule in playbook.rules:
                total_rules_scanned += 1

                if rule.clause_type in seen_clause_types:
                    continue

                matched, matched_keywords = self._match_rule(
                    contract_text, rule
                )

                if not matched:
                    continue

                if not rule.negotiable:
                    continue

                suggestion = self._generate_suggestion(
                    contract_text, rule, matched_keywords, playbook
                )

                suggestions.append(suggestion)
                seen_clause_types.add(rule.clause_type)
                rules_map[rule.clause_type] = rule

        if request.use_llm and suggestions:
            suggestions = self._refine_batch_with_llm(
                suggestions, rules_map
            )

        suggestions.sort(
            key=lambda s: _RISK_SORT_ORDER.get(s.risk_level, 4),
        )

        return RedlineResult(
            suggestions=suggestions,
            total_clauses_scanned=total_rules_scanned,
            negotiable_clauses_found=len(suggestions),
            playbooks_used=[pb.playbook_id for pb in selected_playbooks],
        )
