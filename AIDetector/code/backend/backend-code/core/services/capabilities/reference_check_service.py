import re

from .llm import assess_reference_authenticity


def evaluate_references(*, text_content, references, api_key=None):
    results = []
    for index, reference in enumerate(references):
        llm_auth = assess_reference_authenticity(reference=reference, api_key=api_key)
        authenticity = llm_auth if isinstance(llm_auth, dict) else {
            "score": 0.0,
            "label": "analysis_unavailable",
            "reason": "参考文献真实性分析未能调用 LLM。",
            "source": "api_unavailable",
        }
        results.append(
            {
                "reference_index": index,
                "reference": reference,
                "exists": bool(reference.strip()),
                "authenticity_score": authenticity["score"],
                "authenticity_label": authenticity["label"],
                "authenticity_reason": authenticity["reason"],
                "analysis_source": authenticity.get("source", "llm"),
            }
        )
    return results
