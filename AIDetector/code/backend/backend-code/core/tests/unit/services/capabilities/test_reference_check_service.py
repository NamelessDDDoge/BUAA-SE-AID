"""capabilities/reference_check_service"""
from unittest.mock import patch

import pytest

from core.services.capabilities.reference_check_service import (
    _normalize_authenticity_result,
    evaluate_references,
)

pytestmark = pytest.mark.unit


# ---------- _normalize_authenticity_result ----------

def test_normalize_returns_fallback_when_input_not_dict():
    out = _normalize_authenticity_result(None)
    assert out["authenticity_label"] == "analysis_unavailable"
    assert out["source"] == "api_unavailable"


def test_normalize_returns_fallback_when_score_missing():
    out = _normalize_authenticity_result({"label": "real", "reason": "ok"})
    assert out["authenticity_label"] == "analysis_unavailable"


def test_normalize_returns_fallback_when_label_empty():
    out = _normalize_authenticity_result({"score": 0.9, "label": "", "reason": "ok"})
    assert out["authenticity_label"] == "analysis_unavailable"


def test_normalize_accepts_authenticity_prefixed_keys():
    raw = {
        "authenticity_score": 0.7,
        "authenticity_label": "likely_authentic",
        "authenticity_reason": "matches DOI",
        "source": "llm",
    }
    out = _normalize_authenticity_result(raw)
    assert out["authenticity_score"] == 0.7
    assert out["authenticity_label"] == "likely_authentic"
    assert out["authenticity_reason"] == "matches DOI"
    assert out["source"] == "llm"


def test_normalize_falls_back_to_short_key_aliases():
    raw = {"score": 0.5, "label": "uncertain", "reason": "weak", "source": "llm"}
    out = _normalize_authenticity_result(raw)
    assert out["authenticity_score"] == 0.5
    assert out["authenticity_label"] == "uncertain"


def test_normalize_coerces_score_to_float():
    raw = {"authenticity_score": "0.42", "authenticity_label": "x"}
    out = _normalize_authenticity_result(raw)
    assert out["authenticity_score"] == pytest.approx(0.42)


# ---------- evaluate_references ----------

@patch("core.services.capabilities.reference_check_service.assess_reference_authenticity")
def test_evaluate_returns_one_record_per_reference(mock_assess):
    mock_assess.return_value = {"score": 0.6, "label": "uncertain", "reason": "?"}
    out = evaluate_references(
        text_content="paper body", references=["ref-1", "ref-2", "ref-3"],
    )
    assert len(out) == 3
    assert [r["reference_index"] for r in out] == [0, 1, 2]


@patch("core.services.capabilities.reference_check_service.assess_reference_authenticity")
def test_evaluate_marks_exists_true_for_nonblank(mock_assess):
    mock_assess.return_value = {"score": 0.6, "label": "real", "reason": ""}
    out = evaluate_references(text_content="x", references=["non-blank ref"])
    assert out[0]["exists"] is True


@patch("core.services.capabilities.reference_check_service.assess_reference_authenticity")
def test_evaluate_marks_exists_false_for_blank(mock_assess):
    mock_assess.return_value = {"score": 0.0, "label": "x", "reason": ""}
    out = evaluate_references(text_content="x", references=["   "])
    assert out[0]["exists"] is False


@patch("core.services.capabilities.reference_check_service.assess_reference_authenticity")
def test_evaluate_records_unavailable_when_llm_returns_none(mock_assess):
    mock_assess.return_value = None
    out = evaluate_references(text_content="x", references=["ref"])
    assert out[0]["analysis_source"] == "api_unavailable"
    assert out[0]["authenticity_label"] == "analysis_unavailable"


@patch("core.services.capabilities.reference_check_service.assess_reference_authenticity")
def test_evaluate_empty_references_returns_empty_list(mock_assess):
    out = evaluate_references(text_content="paper", references=[])
    assert out == []
    mock_assess.assert_not_called()
