from .fastdetect_client import detect_text_segment
from .openai_client import (
    assess_data_authenticity_finding,
    assess_reference_authenticity,
    explain_text_segment,
    summarize_paper_overall,
)

__all__ = [
    "detect_text_segment",
    "explain_text_segment",
    "summarize_paper_overall",
    "assess_reference_authenticity",
    "assess_data_authenticity_finding",
]
