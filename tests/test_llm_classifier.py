"""Tests for LLM-Powered Theme Classifier and Fallback Mechanism."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.analysis.llm_classifier import (
    BaseLLMClient,
    GeminiLLMClient,
    MockLLMClient,
    OpenAILLMClient,
    classify_feedback_item,
    get_configured_llm_client,
    parse_llm_json_response,
)
from src.analysis.theme_classifier import (
    THEME_CUSTOMER_SUPPORT,
    THEME_PLATFORM_TRUST,
    THEME_UNCERTAIN,
    ClassifiedFeedback,
)


def test_get_configured_llm_client_missing_credentials():
    """Verify that get_configured_llm_client returns None when no keys or providers are set."""
    with patch.dict("os.environ", {}, clear=True):
        client = get_configured_llm_client()
        assert client is None


def test_get_configured_llm_client_mock_provider():
    """Verify that setting LLM_PROVIDER=mock instantiates MockLLMClient."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "mock"}):
        client = get_configured_llm_client()
        assert isinstance(client, MockLLMClient)


def test_get_configured_llm_client_gemini_provider():
    """Verify that configuring Gemini key instantiates GeminiLLMClient."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test_gemini_key", "LLM_PROVIDER": "gemini"}):
        client = get_configured_llm_client()
        assert isinstance(client, GeminiLLMClient)
        assert client.api_key == "test_gemini_key"


def test_get_configured_llm_client_openai_provider():
    """Verify that configuring OpenAI key instantiates OpenAILLMClient."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test_openai_key", "LLM_PROVIDER": "openai"}):
        client = get_configured_llm_client()
        assert isinstance(client, OpenAILLMClient)
        assert client.api_key == "test_openai_key"


def test_parse_llm_json_response_clean():
    """Verify parsing a valid JSON response from an LLM."""
    raw = json.dumps({
        "primary_theme": THEME_CUSTOMER_SUPPORT,
        "secondary_theme": "",
        "confidence": "high",
        "supporting_evidence": "customer care never replied",
    })
    parsed = parse_llm_json_response(raw)
    assert parsed["primary_theme"] == THEME_CUSTOMER_SUPPORT
    assert parsed["confidence"] == "high"
    assert parsed["supporting_evidence"] == "customer care never replied"


def test_parse_llm_json_response_with_markdown_fences():
    """Verify parsing when the LLM wraps JSON inside markdown code fences."""
    raw = f"```json\n{{\n  \"primary_theme\": \"{THEME_PLATFORM_TRUST}\",\n  \"confidence\": \"medium\",\n  \"supporting_evidence\": \"mandate failed\"\n}}\n```"
    parsed = parse_llm_json_response(raw)
    assert parsed["primary_theme"] == THEME_PLATFORM_TRUST
    assert parsed["confidence"] == "medium"


def test_parse_llm_json_response_invalid_theme_marked_uncertain():
    """Verify that unknown/hallucinated theme strings are mapped to Uncertain."""
    raw = json.dumps({
        "primary_theme": "Invented Fantasy Theme",
        "confidence": "high",
        "supporting_evidence": "none",
    })
    parsed = parse_llm_json_response(raw)
    assert parsed["primary_theme"] == THEME_UNCERTAIN
    assert parsed["confidence"] == "uncertain"


def test_classify_feedback_item_with_none_client_falls_back():
    """Verify that when llm_client is None, it transparently falls back to rule-based classification."""
    item = classify_feedback_item(
        record_id="REC_001",
        source="test_source",
        text="ticket closed without resolution by customer care",
        investor_status="reviewer",
        asset_type="mutual_fund_and_platform",
        llm_client=None,
    )
    assert isinstance(item, ClassifiedFeedback)
    assert item.record_id == "REC_001"
    assert item.primary_theme == THEME_CUSTOMER_SUPPORT
    assert "ticket" in item.supporting_evidence


def test_classify_feedback_item_api_failure_fallback():
    """Verify that if LLM raises a network or timeout error, it falls back without crashing."""
    mock_client = MagicMock(spec=BaseLLMClient)
    mock_client.classify_text.side_effect = RuntimeError("Simulated API timeout")

    item = classify_feedback_item(
        record_id="REC_002",
        source="test_source",
        text="bank mandate failed and auto-debit stuck",
        investor_status="reviewer",
        asset_type="mutual_fund_and_platform",
        llm_client=mock_client,
    )
    # Pipeline should not crash and should fall back to rule-based
    assert item.record_id == "REC_002"
    assert item.primary_theme == THEME_PLATFORM_TRUST


def test_classify_feedback_item_preserves_provenance():
    """Verify that original metadata and feedback text are strictly preserved."""
    client = MockLLMClient()
    text_content = "Very confusing charges deducted from my mutual fund investment"
    item = classify_feedback_item(
        record_id="ID_999",
        source="google_play_b1",
        text=text_content,
        investor_status="playstore_1star",
        asset_type="mutual_fund_and_platform",
        llm_client=client,
    )
    assert item.record_id == "ID_999"
    assert item.source == "google_play_b1"
    assert item.feedback_text == text_content
    assert item.investor_status == "playstore_1star"
    assert item.asset_type == "mutual_fund_and_platform"


def test_ambiguous_feedback_marked_uncertain():
    """Verify that off-topic derivative queries and generic short reviews are marked uncertain."""
    client = MockLLMClient()
    generic_item = classify_feedback_item(
        record_id="REC_AMB_1",
        source="google_play",
        text="good app ok.",
        investor_status="reviewer",
        llm_client=client,
    )
    assert generic_item.primary_theme == THEME_UNCERTAIN
    assert generic_item.confidence == "uncertain"

    derivative_item = classify_feedback_item(
        record_id="REC_AMB_2",
        source="google_play",
        text="Lost 10k in Nifty 50 call option scalper terminal",
        investor_status="reviewer",
        llm_client=client,
    )
    assert derivative_item.primary_theme == THEME_UNCERTAIN
    assert derivative_item.confidence == "uncertain"
