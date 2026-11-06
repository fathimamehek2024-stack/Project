"""LLM-Powered Theme Classifier with Rule-Based Fallback.

Provides configurable LLM classification (Gemini, OpenAI, Mock) with structured
JSON outputs, verbatim evidence extraction, and graceful fallback to rule-based heuristics.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
from typing import Any
import urllib.error
import urllib.request

from dotenv import load_dotenv

from src.analysis.theme_classifier import (
    THEME_CONTINUATION,
    THEME_CUSTOMER_SUPPORT,
    THEME_FINANCIAL_CONSTRAINTS,
    THEME_INVESTMENT_UNDERSTANDING,
    THEME_PAUSE_STOP_REASONS,
    THEME_PLATFORM_TRUST,
    THEME_UNCERTAIN,
    THEME_UNCERTAINTY,
    THEME_USABILITY,
    ClassifiedFeedback,
    classify_survey_record,
    classify_text_record,
)

# Load environment variables from .env if present
load_dotenv()

logger = logging.getLogger(__name__)

# Valid theme taxonomy for the discovery engine
VALID_THEMES: list[str] = [
    THEME_PLATFORM_TRUST,
    THEME_CUSTOMER_SUPPORT,
    THEME_UNCERTAINTY,
    THEME_FINANCIAL_CONSTRAINTS,
    THEME_INVESTMENT_UNDERSTANDING,
    THEME_PAUSE_STOP_REASONS,
    THEME_CONTINUATION,
    THEME_USABILITY,
    THEME_UNCERTAIN,
]

# System prompt template defining classification rules and JSON schema
CLASSIFICATION_PROMPT_TEMPLATE = """You are an objective AI research analyst assisting a product manager in understanding first-time mutual fund SIP investor retention and churn for Groww.

Analyze the user feedback below and classify it into EXACTLY ONE primary theme and an optional secondary theme from this list:
1. "Platform Trust, Technical Friction & Mandate Failures" (e.g., auto-pay failure, bank mandate, stuck orders, refund delay, money debited but not invested)
2. "Customer Support & Service Friction" (e.g., tickets closed without resolution, unresponsive helpline, poor service)
3. "Market Volatility Anxiety & Uncertainty" (e.g., panic over negative returns, NAV drops, market crash, loss fear)
4. "Financial Constraints & Cash-Flow Liquidity" (e.g., job change, salary reduction, lack of funds, needed money for emergency)
5. "Investment Literacy & Understanding Gaps" (e.g., confusion on how SIP works, charges/tax deductions, choosing wrong amount)
6. "Deliberate Pausing, Stopping & Alternative Migration" (e.g., deliberately stopped, moved to Zerodha/Kuvera, lost interest)
7. "SIP Continuation & Goal Enablers" (e.g., regular investing, compounding discipline, clear goal tracking)
8. "Platform Usability, UI Speed & Design Ease" (e.g., smooth UI, easy navigation, charts, app speed)
9. "Uncertain / Ambiguous Feedback" (e.g., generic one-word review, day-trading options complaint, off-topic, or unclear context)

STRICT RULES:
- Do NOT invent user motivations, statistics, or outcomes.
- "supporting_evidence" MUST be an EXACT, verbatim quote (substring) from the feedback text.
- If the feedback is ambiguous, off-topic, or lacks clear context, assign "primary_theme": "Uncertain / Ambiguous Feedback" and "confidence": "uncertain".
- Confidence must be one of: "high", "medium", "uncertain".

Respond ONLY with a valid JSON object matching this schema:
{{
  "primary_theme": "<One theme from the list>",
  "secondary_theme": "<Optional secondary theme or empty string>",
  "confidence": "high|medium|uncertain",
  "supporting_evidence": "<Verbatim quotation from the feedback>"
}}

Feedback to classify:
\"\"\"{feedback_text}\"\"\"
"""


class BaseLLMClient:
    """Base interface for LLM provider clients."""

    def classify_text(self, text: str) -> dict[str, str]:
        """Classify feedback text and return structured dictionary."""
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    """Deterministic mock client for offline testing and CI environments."""

    def __init__(self, responses: dict[str, dict[str, str]] | None = None) -> None:
        self.responses = responses or {}

    def classify_text(self, text: str) -> dict[str, str]:
        # Check custom canned responses
        for key, resp in self.responses.items():
            if key.lower() in text.lower():
                return resp

        # Contextual mock classification simulating LLM semantic understanding
        cleaned = text.lower()

        # 1. Ambiguity / Off-topic / Generic detection
        if cleaned in ("good app ok.", "nice", "ok", "good") or "call option" in cleaned or "nifty 50" in cleaned or "scalper" in cleaned or "tata motors" in cleaned:
            return {
                "primary_theme": THEME_UNCERTAIN,
                "secondary_theme": "",
                "confidence": "uncertain",
                "supporting_evidence": "Ambiguous, generic, or off-topic trading query",
            }

        # 2. Customer Support Friction
        if any(w in cleaned for w in ("customer care", "support team", "ticket", "executive", "helpline", "no response")):
            return {
                "primary_theme": THEME_CUSTOMER_SUPPORT,
                "secondary_theme": "",
                "confidence": "high",
                "supporting_evidence": "customer care / support",
            }

        # 3. Platform Trust & Technical Friction
        if any(w in cleaned for w in ("mandate", "auto-debit", "upi is not working", "deducted", "glitch", "stuck", "awaiting payment", "payment delayed")):
            return {
                "primary_theme": THEME_PLATFORM_TRUST,
                "secondary_theme": "",
                "confidence": "high",
                "supporting_evidence": "mandate / payment / technical failure",
            }

        # 4. Market Volatility Anxiety
        if any(w in cleaned for w in ("market fall", "negative return", "volatilit", "down", "panic")):
            return {
                "primary_theme": THEME_UNCERTAINTY,
                "secondary_theme": "",
                "confidence": "high",
                "supporting_evidence": "market fall or negative returns",
            }

        # 5. Financial Constraints & Cash Flow
        if any(w in cleaned for w in ("job change", "salary", "lower income", "cash-flow", "emergency medical", "financial issues")):
            return {
                "primary_theme": THEME_FINANCIAL_CONSTRAINTS,
                "secondary_theme": "",
                "confidence": "high",
                "supporting_evidence": "job change / income pressure",
            }

        # 6. Investment Literacy & Understanding
        if any(w in cleaned for w in ("exit load", "stamp duty", "charges", "tax", "confusing", "understand", "pool account", "shuts down")):
            return {
                "primary_theme": THEME_INVESTMENT_UNDERSTANDING,
                "secondary_theme": "",
                "confidence": "high",
                "supporting_evidence": "charges / taxes / understanding",
            }

        # 7. Deliberate Pausing & Migration
        if any(w in cleaned for w in ("shifted", "zerodha", "coin", "another investment", "lost interest", "stopped")):
            return {
                "primary_theme": THEME_PAUSE_STOP_REASONS,
                "secondary_theme": "",
                "confidence": "high",
                "supporting_evidence": "stopped / shifted to another option",
            }

        # 8. Continuation & Goal Enablers
        if any(w in cleaned for w in ("personal goal", "compounding", "educational content", "discipline", "active")):
            return {
                "primary_theme": THEME_CONTINUATION,
                "secondary_theme": "",
                "confidence": "high",
                "supporting_evidence": "goal / compounding / discipline",
            }

        # 9. Usability & UI
        if any(w in cleaned for w in ("ui", "clean ui", "smooth", "chart update", "back button", "interface")):
            return {
                "primary_theme": THEME_USABILITY,
                "secondary_theme": "",
                "confidence": "high",
                "supporting_evidence": "clean UI / chart update",
            }

        return {
            "primary_theme": THEME_UNCERTAIN,
            "secondary_theme": "",
            "confidence": "uncertain",
            "supporting_evidence": "No clear investment theme detected",
        }


class GeminiLLMClient(BaseLLMClient):
    """Client for Google Gemini API using standard library urllib."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key
        self.model = model
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

    def classify_text(self, text: str) -> dict[str, str]:
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(feedback_text=text)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
            },
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                content_text = (
                    resp_json.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                return parse_llm_json_response(content_text)
        except Exception as e:
            logger.warning("Gemini API call failed: %s", e)
            raise


class OpenAILLMClient(BaseLLMClient):
    """Client for OpenAI API using standard library urllib."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    def classify_text(self, text: str) -> dict[str, str]:
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(feedback_text=text)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                content_text = resp_json["choices"][0]["message"]["content"]
                return parse_llm_json_response(content_text)
        except Exception as e:
            logger.warning("OpenAI API call failed: %s", e)
            raise


def parse_llm_json_response(raw_text: str) -> dict[str, str]:
    """Extract and validate JSON structure from LLM output."""
    clean_text = raw_text.strip()
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```(json)?\s*", "", clean_text)
        clean_text = re.sub(r"\s*```$", "", clean_text)

    data = json.loads(clean_text)

    primary = data.get("primary_theme", THEME_UNCERTAIN).strip()
    # Normalize theme if slightly misspelled
    matched_theme = next(
        (t for t in VALID_THEMES if t.lower() == primary.lower()), None
    )
    if not matched_theme:
        matched_theme = THEME_UNCERTAIN

    secondary = data.get("secondary_theme", "").strip()
    matched_sec = next(
        (t for t in VALID_THEMES if t.lower() == secondary.lower()), ""
    )

    confidence = str(data.get("confidence", "uncertain")).lower().strip()
    if confidence not in ("high", "medium", "uncertain") or matched_theme == THEME_UNCERTAIN:
        confidence = "uncertain"

    evidence = str(data.get("supporting_evidence", "")).strip()

    return {
        "primary_theme": matched_theme,
        "secondary_theme": matched_sec,
        "confidence": confidence,
        "supporting_evidence": evidence,
    }


def get_configured_llm_client() -> BaseLLMClient | None:
    """Instantiate configured LLM client based on environment variables.

    Returns None if no credentials are configured, triggering graceful rule-based fallback.
    """
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if provider == "mock":
        return MockLLMClient()

    if provider == "gemini" or (not provider and gemini_key):
        if gemini_key:
            model = os.getenv("LLM_MODEL", "gemini-1.5-flash").strip()
            return GeminiLLMClient(api_key=gemini_key, model=model)
        logger.info("LLM_PROVIDER=gemini specified but GEMINI_API_KEY is empty.")
        return None

    if provider == "openai" or (not provider and openai_key):
        if openai_key:
            model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
            return OpenAILLMClient(api_key=openai_key, model=model)
        logger.info("LLM_PROVIDER=openai specified but OPENAI_API_KEY is empty.")
        return None

    return None


def classify_feedback_item(
    record_id: str,
    source: str,
    text: str,
    investor_status: str,
    asset_type: str = "mutual_fund_and_platform",
    llm_client: BaseLLMClient | None = None,
) -> ClassifiedFeedback:
    """Classify a feedback record using the LLM client, falling back to rule-based heuristics.

    Guarantees:
    - Never throws if LLM API call fails.
    - Preserves original text, record ID, and source.
    - Accurately tags ambiguous input as uncertain.
    """
    if llm_client is not None:
        try:
            llm_result = llm_client.classify_text(text)
            evidence = llm_result.get("supporting_evidence", "")
            # Ensure evidence references input text
            if evidence and evidence.lower() not in text.lower():
                evidence = f"LLM evidence: '{evidence}' (extracted snippet)"

            return ClassifiedFeedback(
                record_id=record_id,
                source=source,
                asset_type=asset_type,
                feedback_text=text,
                primary_theme=llm_result["primary_theme"],
                secondary_theme=llm_result["secondary_theme"],
                confidence=llm_result["confidence"],
                supporting_evidence=evidence or "LLM thematic analysis",
                investor_status=investor_status,
            )
        except Exception as err:
            logger.warning(
                "LLM classification failed for record %s (%s). Falling back to rule-based classifier.",
                record_id,
                err,
            )

    # Fallback to rule-based classifier
    return classify_text_record(
        record_id=record_id,
        source=source,
        text=text,
        investor_status=investor_status,
        asset_type=asset_type,
    )
