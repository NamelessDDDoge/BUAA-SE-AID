"""Table data authenticity checks."""
from unittest.mock import patch

import pytest

from core.services.capabilities.data_authenticity_service import evaluate_data_authenticity


pytestmark = pytest.mark.unit


@patch("core.services.capabilities.data_authenticity_service.summarize_data_authenticity")
@patch("core.services.capabilities.data_authenticity_service.assess_table_authenticity")
def test_evaluate_tables_returns_separate_table_results(mock_assess_table, mock_summary):
    mock_assess_table.return_value = {
        "risk_level": "medium",
        "reason": "numeric trend needs verification",
        "evidence_summary": "Ours improves from 81.2 to 91.4.",
        "suspicious_cells": ["Ours / Accuracy"],
    }
    mock_summary.return_value = None

    out = evaluate_data_authenticity(
        [],
        tables=[
            {
                "table_index": 0,
                "source": "pdf_inferred",
                "row_count": 3,
                "column_count": 3,
                "headers": ["Method", "Accuracy", "F1"],
                "rows": [["Baseline", "81.2", "79.5"], ["Ours", "91.4", "90.1"]],
                "text": "Method | Accuracy | F1\nBaseline | 81.2 | 79.5\nOurs | 91.4 | 90.1",
            }
        ],
    )

    assert len(out["table_results"]) == 1
    assert out["table_results"][0]["source"] == "pdf_inferred"
    assert out["table_results"][0]["risk_level"] == "medium"
    assert out["table_results"][0]["headers"] == ["Method", "Accuracy", "F1"]
    assert out["table_results"][0]["rows_preview"] == [["Baseline", "81.2", "79.5"], ["Ours", "91.4", "90.1"]]
    assert out["table_results"][0]["evidence_summary"] == "Ours improves from 81.2 to 91.4."
    assert out["table_results"][0]["suspicious_cells"] == ["Ours / Accuracy"]
    assert out["findings"][0]["source_type"] == "table"
    mock_assess_table.assert_called_once()


@patch("core.services.capabilities.data_authenticity_service.summarize_data_authenticity")
@patch("core.services.capabilities.data_authenticity_service.assess_table_authenticity")
def test_evaluate_tables_prefers_llm_summary(mock_assess_table, mock_summary):
    mock_assess_table.return_value = {"risk_level": "low", "reason": "values are plausible"}
    mock_summary.return_value = {
        "risk_level": "low",
        "summary": "LLM summary based on extracted table headers and rows.",
        "key_points": ["checked table structure"],
    }

    out = evaluate_data_authenticity(
        [],
        tables=[
            {
                "table_index": 0,
                "source": "docx",
                "row_count": 2,
                "column_count": 2,
                "headers": ["Metric", "Value"],
                "rows": [["Accuracy", "0.91"]],
                "text": "Metric | Value\nAccuracy | 0.91",
            }
        ],
    )

    assert out["summary"] == "LLM summary based on extracted table headers and rows."
    assert out["summary_source"] == "llm"
    assert out["summary_risk_level"] == "low"
    assert out["summary_key_points"] == ["checked table structure"]
