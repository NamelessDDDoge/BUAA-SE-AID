from .llm import assess_reference_authenticity


def evaluate_references(*, text_content, references, api_key=None):
    results = []
    for index, reference in enumerate(references):
        authenticity = _normalize_authenticity_result(
            assess_reference_authenticity(reference=reference, api_key=api_key)
        )
        results.append(
            {
                "reference_index": index,
                "reference": reference,
                "exists": bool((reference or "").strip()),
                "authenticity_score": authenticity["authenticity_score"],
                "authenticity_label": authenticity["authenticity_label"],
                "authenticity_reason": authenticity["authenticity_reason"],
                "analysis_source": authenticity["source"],
            }
        )
    return results


def _normalize_authenticity_result(llm_auth):
    fallback = {
        "authenticity_score": 0.0,
        "authenticity_label": "analysis_unavailable",
        "authenticity_reason": "参考文献真实性分析未能调用 LLM。",
        "source": "api_unavailable",
    }
    if not isinstance(llm_auth, dict):
        return fallback

    score = llm_auth.get("authenticity_score", llm_auth.get("score"))
    label = llm_auth.get("authenticity_label", llm_auth.get("label"))
    reason = llm_auth.get("authenticity_reason", llm_auth.get("reason"))
    source = llm_auth.get("source", "llm")

    if score is None or label in (None, ""):
        return fallback

    return {
        "authenticity_score": float(score),
        "authenticity_label": str(label),
        "authenticity_reason": str(reason or fallback["authenticity_reason"]),
        "source": str(source),
    }
