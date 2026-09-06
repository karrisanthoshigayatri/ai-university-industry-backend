"""Qwen2.5 AI service abstraction.

Two backends:
- MockAIService  (AI_ENABLED=false, default): deterministic structured output.
- Qwen25AIService (AI_ENABLED=true): calls Qwen2.5 via Ollama or any
  OpenAI-compatible endpoint configured through environment variables.

No credentials are ever hardcoded or logged.
"""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from functools import lru_cache

from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings


logger = logging.getLogger(__name__)


# ── Structured AI output schema ────────────────────────────────────────────────

class AICategoryItem(BaseModel):
    capability_name: str
    category_role: str = "Primary"          # Primary | Secondary
    confidence: float = Field(ge=0.0, le=1.0)


class AIPriorityOutput(BaseModel):
    priority_level: str = "Medium"           # Low | Medium | High | Critical
    priority_score: float = Field(ge=0.0, le=1.0)
    severity_score: float = Field(ge=0.0, le=1.0)
    urgency_score: float = Field(ge=0.0, le=1.0)
    affected_population: int = 0
    geographic_spread: float = Field(default=0.0, ge=0.0, le=1.0)
    feasibility_score: float = Field(ge=0.0, le=1.0)
    strategic_relevance: float = Field(ge=0.0, le=1.0)
    factors: list[str] = []


class AIRequirementsOutput(BaseModel):
    required_support: str = ""
    geographic_requirements: str = ""
    eligibility_requirements: str = ""
    timeline: str = ""
    constraints: str = ""


class AICapabilityItem(BaseModel):
    capability_name: str
    requirement_type: str = "Domain"         # Domain | Skill | Expertise | Technology | Resource | Support Capability
    required_level: float = Field(default=0.5, ge=0.0, le=1.0)
    criticality: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class AIAnalysisOutput(BaseModel):
    """Validated structured output from the AI model."""
    categories: list[AICategoryItem] = []
    priority: AIPriorityOutput
    requirements: AIRequirementsOutput
    capabilities: list[AICapabilityItem] = []


# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an AI assistant for a government Smart Problem-to-Impact platform.
Given a citizen-submitted problem, return ONLY valid JSON with this exact structure:
{
  "categories": [
    {"capability_name": "...", "category_role": "Primary", "confidence": 0.9}
  ],
  "priority": {
    "priority_level": "High",
    "priority_score": 0.75,
    "severity_score": 0.8,
    "urgency_score": 0.7,
    "affected_population": 5000,
    "geographic_spread": 0.4,
    "feasibility_score": 0.6,
    "strategic_relevance": 0.7,
    "factors": ["public health", "infrastructure"]
  },
  "requirements": {
    "required_support": "...",
    "geographic_requirements": "...",
    "eligibility_requirements": "...",
    "timeline": "...",
    "constraints": "..."
  },
  "capabilities": [
    {"capability_name": "...", "requirement_type": "Domain", "required_level": 0.7, "criticality": 0.8, "confidence": 0.85}
  ]
}
Do not include any text outside the JSON object."""


# ── Abstract base ──────────────────────────────────────────────────────────────

class AIService(ABC):
    @abstractmethod
    def analyse(self, title: str, description: str, location: str, source_type: str) -> AIAnalysisOutput:
        """Return structured analysis for the given problem text."""


# ── Mock backend ───────────────────────────────────────────────────────────────

class MockAIService(AIService):
    """Returns deterministic mock output based on problem text hash.
    No ML dependencies required.
    """

    def analyse(self, title: str, description: str, location: str, source_type: str) -> AIAnalysisOutput:
        text = f"{title} {description} {location}".lower()
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)

        # Deterministic scores derived from the hash
        def score(offset: int) -> float:
            return round(((h >> offset) & 0xFF) / 255.0, 4)

        levels = ["Low", "Medium", "High", "Critical"]
        priority_level = levels[(h >> 4) % 4]

        keywords_infra    = any(w in text for w in ["road", "bridge", "pipe", "water", "drainage", "pothole"])
        keywords_health   = any(w in text for w in ["health", "hospital", "disease", "medical", "sanitation"])
        keywords_edu      = any(w in text for w in ["school", "education", "student", "teacher", "college"])
        keywords_env      = any(w in text for w in ["garbage", "waste", "pollution", "tree", "forest"])
        keywords_electric = any(w in text for w in ["light", "power", "electricity", "current"])

        primary_cap   = "Infrastructure Management"   if keywords_infra  else \
                        "Public Health Services"      if keywords_health else \
                        "Education Administration"    if keywords_edu    else \
                        "Environmental Management"    if keywords_env    else \
                        "Electrical Infrastructure"   if keywords_electric else \
                        "General Public Services"

        secondary_cap = "Civil Engineering"           if keywords_infra  else \
                        "Epidemiology"                if keywords_health else \
                        "Curriculum Development"      if keywords_edu    else \
                        "Waste Management"            if keywords_env    else \
                        "Power Systems Engineering"   if keywords_electric else \
                        "Urban Planning"

        factors = []
        if keywords_infra:    factors.append("infrastructure deficit")
        if keywords_health:   factors.append("public health risk")
        if keywords_edu:      factors.append("education access gap")
        if keywords_env:      factors.append("environmental hazard")
        if not factors:       factors = ["civic service gap"]

        return AIAnalysisOutput(
            categories=[
                AICategoryItem(capability_name=primary_cap,   category_role="Primary",   confidence=round(score(0) * 0.4 + 0.55, 4)),
                AICategoryItem(capability_name=secondary_cap, category_role="Secondary", confidence=round(score(8) * 0.3 + 0.40, 4)),
            ],
            priority=AIPriorityOutput(
                priority_level=priority_level,
                priority_score=score(0),
                severity_score=score(8),
                urgency_score=score(16),
                affected_population=((h >> 24) & 0xFFF) * 10,
                geographic_spread=score(32),
                feasibility_score=score(40),
                strategic_relevance=score(48),
                factors=factors,
            ),
            requirements=AIRequirementsOutput(
                required_support=f"Technical support in {primary_cap.lower()} domain with local implementation capacity.",
                geographic_requirements=f"Intervention required in {location or 'the affected area'}.",
                eligibility_requirements="Government-registered HEI or research institution with relevant domain expertise.",
                timeline="Short to medium term: 3-12 months depending on scope.",
                constraints="Budget constraints and inter-departmental coordination required.",
            ),
            capabilities=[
                AICapabilityItem(
                    capability_name=primary_cap,
                    requirement_type="Domain",
                    required_level=score(0),
                    criticality=score(8),
                    confidence=round(score(0) * 0.4 + 0.55, 4),
                ),
                AICapabilityItem(
                    capability_name="Project Management",
                    requirement_type="Skill",
                    required_level=0.6,
                    criticality=0.5,
                    confidence=0.75,
                ),
                AICapabilityItem(
                    capability_name="Field Research",
                    requirement_type="Expertise",
                    required_level=score(16),
                    criticality=score(24),
                    confidence=round(score(32) * 0.3 + 0.5, 4),
                ),
            ],
        )


# ── Real Qwen2.5 backend ───────────────────────────────────────────────────────

class Qwen25AIService(AIService):
    """Calls Qwen2.5 through Ollama or any OpenAI-compatible endpoint.

    Model is lazy-loaded on first use.
    Requires: pip install openai
    """

    def __init__(self, model: str, base_url: str, api_key: str) -> None:
        self._model = model
        self._base_url = base_url
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore[import]
            self._client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key or "ollama",
            )
            return self._client
        except ImportError as exc:
            raise RuntimeError(
                "openai package is not installed. "
                "Run: pip install openai  "
                "or set AI_ENABLED=false to use mock mode."
            ) from exc

    def analyse(self, title: str, description: str, location: str, source_type: str) -> AIAnalysisOutput:
        user_message = (
            f"Problem Title: {title}\n"
            f"Description: {description}\n"
            f"Location: {location or 'Not specified'}\n"
            f"Source Type: {source_type}"
        )
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            raw_text = response.choices[0].message.content or ""
            # Strip markdown code fences if present
            raw_text = raw_text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            parsed = json.loads(raw_text)
            return AIAnalysisOutput.model_validate(parsed)
        except json.JSONDecodeError as exc:
            logger.error("Qwen2.5 returned invalid JSON: %s", type(exc).__name__)
            raise ValueError("AI model returned invalid JSON. Analysis aborted.") from exc
        except ValidationError as exc:
            logger.error("Qwen2.5 output failed schema validation: %s", type(exc).__name__)
            raise ValueError("AI model output did not match expected schema.") from exc
        except Exception as exc:
            logger.error("Qwen2.5 call failed: %s", type(exc).__name__)
            raise ValueError(f"AI analysis failed: {type(exc).__name__}") from exc


# ── Factory ────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_ai_service() -> AIService:
    """Return the configured AI service (singleton)."""
    settings = get_settings()
    if settings.ai_enabled:
        logger.info("AI service: Qwen2.5 model='%s' provider='%s'", settings.qwen_model, settings.ai_provider)
        return Qwen25AIService(
            model=settings.qwen_model,
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
        )
    logger.info("AI service: mock (AI_ENABLED=false)")
    return MockAIService()
