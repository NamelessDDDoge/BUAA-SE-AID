from .fastdetect_client import detect_text_segment
from .openai_client import (
    analyze_review_text,
    assess_data_authenticity_finding,
    assess_reference_authenticity,
    assess_table_authenticity,
    explain_text_segment,
    summarize_data_authenticity,
    summarize_paper_overall,
)

__all__ = [
    "detect_text_segment",
    "explain_text_segment",
    "summarize_paper_overall",
    "analyze_review_text",
    "assess_reference_authenticity",
    "assess_data_authenticity_finding",
    "assess_table_authenticity",
    "summarize_data_authenticity",
]
