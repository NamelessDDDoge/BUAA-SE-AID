"""capabilities/data_authenticity_service"""
from unittest.mock import patch

import pytest

from core.services.capabilities.data_authenticity_service import (
    _build_summary,
    evaluate_data_authenticity,
)

pytestmark = pytest.mark.unit


# ---------- _build_summary ----------

def test_summary_when_llm_not_invoked_at_all():
    msg = _build_summary([], llm_invoked=False, llm_error=None)
    assert "未能调用 LLM" in msg


def test_summary_when_llm_error_is_present():
    msg = _build_summary([], llm_invoked=False, llm_error="timeout")
    assert "调用 LLM 失败" in msg
    assert "timeout" in msg


def test_summary_no_findings_when_llm_invoked():
    msg = _build_summary([], llm_invoked=True, llm_error=None)
    assert "未发现明显" in msg


def test_summary_with_high_risk_finding_marks_overall_high():
    findings = [{"risk_level": "high"}]
    msg = _build_summary(findings, llm_invoked=True)
    assert "高风险" in msg


def test_summary_threshold_8_for_medium_overall():
    # 4 medium = weighted 8, no high
    findings = [{"risk_level": "medium"}] * 4
    msg = _build_summary(findings, llm_invoked=True)
    assert "中风险" in msg


def test_summary_lower_weight_yields_low_overall():
    # 2 low = weighted 2, < 8, no high
    findings = [{"risk_level": "low"}, {"risk_level": "low"}]
    msg = _build_summary(findings, llm_invoked=True)
    assert "低风险" in msg


def test_summary_includes_count_of_findings():
    findings = [{"risk_level": "low"}, {"risk_level": "medium"}, {"risk_level": "high"}]
    msg = _build_summary(findings, llm_invoked=True)
    assert "3 项" in msg


# ---------- evaluate_data_authenticity ----------

@patch("core.services.capabilities.data_authenticity_service.assess_data_authenticity_finding")
@patch("core.services.capabilities.data_authenticity_service.summarize_data_authenticity")
def test_evaluate_skips_paragraphs_with_blank_text(mock_summary, mock_assess):
    mock_summary.return_value = None
    paragraphs = [
        {"paragraph_index": 0, "text": "   "},
        {"paragraph_index": 1, "text": ""},
    ]
    out = evaluate_data_authenticity(paragraphs)
    assert out["findings"] == []
    mock_assess.assert_not_called()


@patch("core.services.capabilities.data_authenticity_service.assess_data_authenticity_finding")
@patch("core.services.capabilities.data_authenticity_service.summarize_data_authenticity")
def test_evaluate_records_error_and_continues(mock_summary, mock_assess):
    mock_summary.return_value = None
    mock_assess.side_effect = [
        {"error": "boom"},
        {"risk_level": "low", "reason": "ok"},
    ]
    paragraphs = [
        {"paragraph_index": 0, "text": "paragraph one"},
        {"paragraph_index": 1, "text": "paragraph two"},
    ]
    out = evaluate_data_authenticity(paragraphs)
    assert len(out["findings"]) == 1
    assert out["findings"][0]["risk_level"] == "low"
    assert out["findings"][0]["paragraph_index"] == 1


@patch("core.services.capabilities.data_authenticity_service.assess_data_authenticity_finding")
@patch("core.services.capabilities.data_authenticity_service.summarize_data_authenticity")
def test_evaluate_ignores_findings_without_valid_risk_level(mock_summary, mock_assess):
    mock_summary.return_value = None
    mock_assess.return_value = {"risk_level": "unknown", "reason": "?"}
    out = evaluate_data_authenticity([{"paragraph_index": 0, "text": "text"}])
    assert out["findings"] == []


@patch("core.services.capabilities.data_authenticity_service.assess_data_authenticity_finding")
@patch("core.services.capabilities.data_authenticity_service.summarize_data_authenticity")
def test_evaluate_keeps_high_risk_findings(mock_summary, mock_assess):
    mock_summary.return_value = None
    mock_assess.return_value = {"risk_level": "high", "reason": "fabricated"}
    out = evaluate_data_authenticity([{"paragraph_index": 5, "text": "claim text"}])
    assert len(out["findings"]) == 1
    f = out["findings"][0]
    assert f["risk_level"] == "high"
    assert f["paragraph_index"] == 5
    assert f["analysis_source"] == "llm"
    assert "claim_text" in f and "evidence" in f


@patch("core.services.capabilities.data_authenticity_service.assess_data_authenticity_finding")
@patch("core.services.capabilities.data_authenticity_service.summarize_data_authenticity")
def test_evaluate_returns_summary_with_count(mock_summary, mock_assess):
    mock_summary.return_value = None
    mock_assess.return_value = {"risk_level": "medium", "reason": "ok"}
    paragraphs = [{"paragraph_index": i, "text": f"p{i}"} for i in range(3)]
    out = evaluate_data_authenticity(paragraphs)
    assert "3 项" in out["summary"]


def test_evaluate_handles_none_paragraph_list_gracefully():
    out = evaluate_data_authenticity(None)
    assert out["findings"] == []
    assert "未能调用 LLM" in out["summary"]
