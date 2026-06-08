"""capabilities/llm_analysis_service"""
from unittest.mock import patch

import pytest

from core.services.capabilities import llm_analysis_service as svc

pytestmark = pytest.mark.unit


# ---------- _risk_level_from_score ----------

@pytest.mark.parametrize("score, expected", [
    (0, "low"),
    (39, "low"),
    (40, "medium"),
    (69, "medium"),
    (70, "high"),
    (100, "high"),
])
def test_risk_level_from_score_boundaries(score, expected):
    assert svc._risk_level_from_score(score) == expected


# ---------- _minimum_risk_level_from_evidence ----------

def test_evidence_high_when_three_confirmed_ai():
    assert svc._minimum_risk_level_from_evidence(
        confirmed_count=3, reference_high_risk_count=0,
    ) == "high"


def test_evidence_high_when_two_confirmed_plus_high_ref():
    assert svc._minimum_risk_level_from_evidence(
        confirmed_count=2, reference_high_risk_count=1,
    ) == "high"


def test_evidence_medium_when_only_one_signal():
    assert svc._minimum_risk_level_from_evidence(
        confirmed_count=1, reference_high_risk_count=0,
    ) == "medium"
    assert svc._minimum_risk_level_from_evidence(
        confirmed_count=0, reference_high_risk_count=1,
    ) == "medium"


def test_evidence_low_when_no_signal():
    assert svc._minimum_risk_level_from_evidence(
        confirmed_count=0, reference_high_risk_count=0,
    ) == "low"


# ---------- _align_score_with_level ----------

def test_align_score_raises_to_70_when_level_high():
    assert svc._align_score_with_level(30, "high") == 70
    assert svc._align_score_with_level(80, "high") == 80


def test_align_score_raises_to_40_when_level_medium():
    assert svc._align_score_with_level(20, "medium") == 40
    assert svc._align_score_with_level(60, "medium") == 60


def test_align_score_unchanged_when_level_low():
    assert svc._align_score_with_level(25, "low") == 25


# ---------- _normalize_risk_level / _risk_rank / _max_risk_level ----------

@pytest.mark.parametrize("raw, expected", [
    ("HIGH", "high"),
    (" medium ", "medium"),
    ("low", "low"),
    ("garbage", "low"),
    (None, "low"),
    ("", "low"),
])
def test_normalize_risk_level(raw, expected):
    assert svc._normalize_risk_level(raw) == expected


def test_risk_rank_ordering():
    assert svc._risk_rank("high") > svc._risk_rank("medium") > svc._risk_rank("low")


def test_max_risk_level_picks_highest():
    assert svc._max_risk_level("low", "medium", "high") == "high"
    assert svc._max_risk_level("low", "medium") == "medium"
    assert svc._max_risk_level("low", "low") == "low"


# ---------- _rule_based_conclusion ----------

def test_rule_based_conclusion_high():
    msg = svc._rule_based_conclusion("high", 0, 0)
    assert "高风险" in msg


def test_rule_based_conclusion_medium_with_evidence():
    msg = svc._rule_based_conclusion("medium", confirmed_count=1, reference_high_risk_count=0)
    assert "明确风险证据" in msg


def test_rule_based_conclusion_medium_without_evidence():
    msg = svc._rule_based_conclusion("medium", 0, 0)
    assert "中等风险" in msg


def test_rule_based_conclusion_low():
    msg = svc._rule_based_conclusion("low", 0, 0)
    assert "整体风险较低" in msg


# ---------- build_suspicious_paragraph_explanations ----------

@patch("core.services.capabilities.llm_analysis_service.explain_text_segment")
def test_explanations_skip_below_threshold(mock_explain):
    mock_explain.return_value = "boom"
    paragraphs = [
        {"paragraph_index": 0, "text": "a", "probability": 0.2},
        {"paragraph_index": 1, "text": "b", "probability": 0.9},
    ]
    out = svc.build_suspicious_paragraph_explanations(paragraphs, suspicious_threshold=0.5)
    assert len(out) == 1
    assert out[0]["paragraph_index"] == 1
    mock_explain.assert_called_once()


@patch("core.services.capabilities.llm_analysis_service.explain_text_segment")
def test_explanations_include_explanation_text(mock_explain):
    mock_explain.return_value = "this is suspicious because X"
    out = svc.build_suspicious_paragraph_explanations(
        [{"paragraph_index": 0, "text": "t", "probability": 0.7}],
        suspicious_threshold=0.5,
    )
    assert out[0]["explanation"] == "this is suspicious because X"
    assert out[0]["text"] == "t"


# ---------- build_overall_paper_evaluation ----------

@patch("core.services.capabilities.llm_analysis_service.summarize_paper_overall")
def test_overall_evaluation_low_risk_path(mock_summary):
    mock_summary.return_value = {"risk_level": "low", "summary": "low risk", "key_concerns": [], "suggestions": []}
    out = svc.build_overall_paper_evaluation(
        paragraph_results=[{"label": "clean"}] * 10,
        confirmed_ai_paragraphs=[],
        reference_results=[],
        data_authenticity_results={"enabled": False, "findings": []},
    )
    assert out["risk_level"] == "low"
    assert out["summary"] == "low risk"
    assert out["summary_source"] == "llm_prompt"


@patch("core.services.capabilities.llm_analysis_service.summarize_paper_overall")
def test_overall_evaluation_uses_data_risk_only_when_enabled(mock_summary):
    mock_summary.return_value = {"risk_level": "low", "summary": "low", "key_concerns": [], "suggestions": []}

    disabled = svc.build_overall_paper_evaluation(
        paragraph_results=[{"label": "clean"}] * 10,
        confirmed_ai_paragraphs=[],
        reference_results=[],
        data_authenticity_results={
            "enabled": False,
            "findings": [{"risk_level": "high"}],
        },
    )
    enabled = svc.build_overall_paper_evaluation(
        paragraph_results=[{"label": "clean"}] * 10,
        confirmed_ai_paragraphs=[],
        reference_results=[],
        data_authenticity_results={
            "enabled": True,
            "findings": [{"risk_level": "high"}],
        },
    )

    assert "high_risk_data_findings" not in disabled["evidence"]
    assert disabled["risk_level"] == "low"
    assert enabled["evidence"]["high_risk_data_findings"] == 1
    assert enabled["risk_level"] == "medium"


@patch("core.services.capabilities.llm_analysis_service.summarize_paper_overall")
def test_overall_evaluation_high_when_evidence_forces_high(mock_summary):
    # LLM 报告 low，但证据规则要求 high → 应被提升
    mock_summary.return_value = {"risk_level": "low", "summary": "low", "key_concerns": [], "suggestions": []}
    out = svc.build_overall_paper_evaluation(
        paragraph_results=[{"label": "suspicious"}] * 5,
        confirmed_ai_paragraphs=[1, 2, 3, 4],  # >=3 → high
        reference_results=[],
        data_authenticity_results=None,
    )
    assert out["risk_level"] == "high"
    assert out["risk_score"] >= 70
    # LLM 的 summary 与级别不一致，应回退到 rule-based
    assert out["summary_source"] == "rule_based"
    assert "高风险" in out["summary"]


@patch("core.services.capabilities.llm_analysis_service.summarize_paper_overall")
def test_overall_evaluation_handles_none_inputs(mock_summary):
    mock_summary.return_value = {"risk_level": "low", "summary": "ok", "key_concerns": [], "suggestions": []}
    out = svc.build_overall_paper_evaluation(
        paragraph_results=None,
        confirmed_ai_paragraphs=None,
        reference_results=None,
        data_authenticity_results=None,
    )
    assert out["risk_level"] == "low"
    assert out["evidence"]["total_paragraphs"] == 0
    assert out["evidence"]["suspicious_paragraphs"] == 0
