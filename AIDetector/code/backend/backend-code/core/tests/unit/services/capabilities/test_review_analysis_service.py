"""capabilities/review_analysis_service"""
from unittest.mock import patch

import pytest

from core.services.capabilities import review_analysis_service as svc

pytestmark = pytest.mark.unit


@patch("core.services.capabilities.review_analysis_service.analyze_review_text")
def test_evaluate_returns_overall_and_paragraph_results_on_llm_success(mock_llm):
    mock_llm.return_value = {
        "overall": {
            "template_like_level": "high",
            "wrongness_level": "medium",
            "relevance_level": "high",
            "summary": "ok",
            "key_findings": ["a"],
            "suggestions": ["b"],
        },
        "paragraph_results": [
            {"review_paragraph_index": 0, "label": "ok"},
        ],
    }
    out = svc.evaluate_review_analysis(
        paper_document={"text_content": "paper body"},
        review_document={"paragraphs": ["review 1"]},
    )
    assert out["overall"]["source"] == "llm"
    assert out["overall"]["template_like_level"] == "high"
    assert len(out["paragraph_results"]) == 1
    assert out["paragraph_results"][0]["analysis_source"] == "llm"


@patch("core.services.capabilities.review_analysis_service.analyze_review_text")
def test_evaluate_returns_api_unavailable_on_llm_error_dict(mock_llm):
    mock_llm.return_value = {"error": "401 unauthorized"}
    out = svc.evaluate_review_analysis(
        paper_document={"text_content": "x"},
        review_document={"paragraphs": ["r"]},
    )
    assert out["overall"]["source"] == "api_unavailable"
    assert "401" in out["overall"]["suggestions"][0]
    assert out["paragraph_results"] == []


@patch("core.services.capabilities.review_analysis_service.get_llm_runtime_config")
@patch("core.services.capabilities.review_analysis_service.analyze_review_text")
def test_evaluate_returns_api_unavailable_when_llm_returns_non_dict(mock_llm, mock_cfg):
    mock_llm.return_value = "not a dict"
    mock_cfg.return_value = {"endpoint": "", "key": ""}
    out = svc.evaluate_review_analysis(
        paper_document={"text_content": "x"},
        review_document={"paragraphs": ["r"]},
    )
    assert out["overall"]["source"] == "api_unavailable"
    assert "endpoint" in out["overall"]["suggestions"][0]


@patch("core.services.capabilities.review_analysis_service.get_llm_runtime_config")
@patch("core.services.capabilities.review_analysis_service.analyze_review_text")
def test_evaluate_suggests_connectivity_check_when_creds_present(mock_llm, mock_cfg):
    mock_llm.return_value = "x"
    mock_cfg.return_value = {"endpoint": "https://x", "key": "sk-xxx"}
    out = svc.evaluate_review_analysis(
        paper_document={"text_content": "x"},
        review_document={"paragraphs": ["r"]},
    )
    assert "连通性" in out["overall"]["suggestions"][0] or "JSON" in out["overall"]["suggestions"][0]


@patch("core.services.capabilities.review_analysis_service.analyze_review_text")
def test_evaluate_truncates_paper_text_to_max_chars(mock_llm):
    mock_llm.return_value = {"overall": {}, "paragraph_results": []}
    svc.evaluate_review_analysis(
        paper_document={"text_content": "x" * 20000},
        review_document={"paragraphs": ["r"]},
    )
    # 检查传给 LLM 的 paper_text 被截断
    call_kwargs = mock_llm.call_args.kwargs
    assert len(call_kwargs["paper_text"]) == svc.MAX_PAPER_TEXT_CHARS


@patch("core.services.capabilities.review_analysis_service.analyze_review_text")
def test_evaluate_limits_review_paragraphs_to_max_count(mock_llm):
    mock_llm.return_value = {"overall": {}, "paragraph_results": []}
    svc.evaluate_review_analysis(
        paper_document={"text_content": "x"},
        review_document={"paragraphs": [f"p{i}" for i in range(50)]},
    )
    call_kwargs = mock_llm.call_args.kwargs
    assert len(call_kwargs["review_paragraphs"]) == svc.MAX_REVIEW_PARAGRAPHS


@patch("core.services.capabilities.review_analysis_service.analyze_review_text")
def test_evaluate_skips_blank_paragraphs_when_building_input(mock_llm):
    mock_llm.return_value = {"overall": {}, "paragraph_results": []}
    svc.evaluate_review_analysis(
        paper_document={"text_content": "x"},
        review_document={"paragraphs": ["", "  ", "real text", None]},
    )
    call_kwargs = mock_llm.call_args.kwargs
    # 只有 "real text" 会被保留
    assert len(call_kwargs["review_paragraphs"]) == 1
    assert call_kwargs["review_paragraphs"][0]["text"] == "real text"
