"""Table data authenticity checks."""
from unittest.mock import patch

import pytest

from core.services.capabilities.data_authenticity_service import evaluate_data_authenticity


pytestmark = pytest.mark.unit


@patch("core.services.capabilities.data_authenticity_service.assess_data_authenticity_finding")
def test_evaluate_tables_returns_separate_table_results(mock_assess):
    mock_assess.return_value = {"risk_level": "medium", "reason": "numeric trend needs verification"}

    out = evaluate_data_authenticity(
        [],
        tables=[
            {
                "table_index": 0,
                "source": "pdf_inferred",
                "row_count": 3,
                "column_count": 3,
                "headers": ["Method", "Accuracy", "F1"],
                "text": "Method | Accuracy | F1\nBaseline | 81.2 | 79.5\nOurs | 91.4 | 90.1",
            }
        ],
    )

    assert len(out["table_results"]) == 1
    assert out["table_results"][0]["source"] == "pdf_inferred"
    assert out["table_results"][0]["risk_level"] == "medium"
    assert out["findings"][0]["source_type"] == "table"
