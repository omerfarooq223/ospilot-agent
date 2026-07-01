from __future__ import annotations

import json

import agents.diagnosis_agent as diagnosis_agent
from agents.diagnosis_agent import diagnose
from core.models import DiagnosisResult, Observation, SystemMetrics


def _observation() -> Observation:
    return Observation(
        metrics=SystemMetrics(
            cpu_percent=10,
            ram_percent=20,
            disk_percent=30,
            available_disk_bytes=1000,
            total_disk_bytes=2000,
        )
    )


def test_diagnosis_fallback_returns_structured_result(monkeypatch) -> None:
    monkeypatch.setattr(diagnosis_agent, "GROQ_API_KEY", "")
    result = diagnose(_observation())
    assert isinstance(result, DiagnosisResult)
    assert result.summary
    assert result.used_fallback is True
    assert result.urgency_level in {"low", "medium", "high"}
    assert result.recommended_scenario in {"conservative", "balanced", "deep"}
    assert isinstance(result.agent_confidence, int)
    assert 0 <= result.agent_confidence <= 100


def test_diagnosis_uses_structured_llm_response(monkeypatch) -> None:
    payload = {
        "summary": "Structured agent summary.",
        "top_risks": ["Risk one"],
        "recommended_scenario": "balanced",
        "urgency_level": "medium",
        "agent_confidence": 82,
    }

    class _Message:
        content = json.dumps(payload)

    class _Choice:
        message = _Message()

    class _Response:
        choices = [_Choice()]

    class _Completions:
        def create(self, **kwargs):
            return _Response()

    class _Chat:
        completions = _Completions()

    class _FakeGroq:
        def __init__(self, api_key):
            self.chat = _Chat()

    monkeypatch.setattr(diagnosis_agent, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(diagnosis_agent, "Groq", _FakeGroq)
    result = diagnose(_observation())

    assert result.used_fallback is False
    assert result.summary == "Structured agent summary."
    assert result.top_risks == ["Risk one"]
    assert result.agent_confidence == 82


def test_diagnosis_falls_back_when_llm_fails(monkeypatch) -> None:
    class _FailingGroq:
        def __init__(self, api_key):
            raise RuntimeError("network unavailable")

    monkeypatch.setattr(diagnosis_agent, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(diagnosis_agent, "Groq", _FailingGroq)
    result = diagnose(_observation())

    assert result.used_fallback is True


def test_old_observation_helper_removed() -> None:
    observation = Observation(
        metrics=SystemMetrics(
            cpu_percent=10,
            ram_percent=20,
            disk_percent=30,
            available_disk_bytes=1000,
            total_disk_bytes=2000,
        )
    )
    assert observation.metrics.cpu_percent == 10
