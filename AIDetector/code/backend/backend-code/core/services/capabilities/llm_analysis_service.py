from .llm import explain_text_segment, summarize_paper_overall


def build_suspicious_paragraph_explanations(paragraph_results, *, api_key=None, llm_model_name=None, suspicious_threshold=0.5):
    explanations = []
    for result in paragraph_results:
        if float(result.get("probability", 0) or 0) < suspicious_threshold:
            continue
        explanations.append(
            {
                "paragraph_index": result["paragraph_index"],
                "text": result["text"],
                "probability": result["probability"],
                "explanation": explain_text_segment(
                    text=result["text"],
                    score=float(result["probability"]),
                    api_key=api_key,
        llm_model_name=llm_model_name,
                ),
            }
        )
    return explanations


def build_overall_paper_evaluation(
    *,
    paragraph_results,
    confirmed_ai_paragraphs,
    reference_results,
    data_authenticity_results=None,
    api_key=None,
    llm_model_name=None,
):
    total_paragraphs = len(paragraph_results or [])
    suspicious_count = sum(1 for item in (paragraph_results or []) if item.get("label") == "suspicious")
    confirmed_count = len(confirmed_ai_paragraphs or [])
    reference_high_risk_count = sum(
        1
        for item in (reference_results or [])
        if item.get("authenticity_label") in {"high_risk", "missing"}
    )
    data_authenticity_enabled = (
        isinstance(data_authenticity_results, dict)
        and data_authenticity_results.get("enabled") is True
    )
    data_findings = []
    if data_authenticity_enabled:
        data_findings = data_authenticity_results.get("findings") or []
    data_high_risk_count = sum(1 for item in data_findings if item.get("risk_level") == "high")

    risk_score = 0
    if total_paragraphs > 0:
        risk_score += min(35, int((suspicious_count / total_paragraphs) * 35))
    risk_score += min(40, confirmed_count * 18)
    risk_score += min(15, reference_high_risk_count * 10)
    risk_score += min(10, data_high_risk_count * 8)

    score_level = _risk_level_from_score(risk_score)
    evidence_level = _minimum_risk_level_from_evidence(
        confirmed_count=confirmed_count,
        reference_high_risk_count=reference_high_risk_count,
        data_high_risk_count=data_high_risk_count,
    )
    level = _max_risk_level(score_level, evidence_level)
    risk_score = _align_score_with_level(risk_score, level)
    conclusion = _rule_based_conclusion(level, confirmed_count, reference_high_risk_count, data_high_risk_count)

    evidence = {
        "total_paragraphs": total_paragraphs,
        "suspicious_paragraphs": suspicious_count,
        "confirmed_ai_paragraphs": confirmed_count,
        "high_risk_references": reference_high_risk_count,
    }
    if data_authenticity_enabled:
        evidence["high_risk_data_findings"] = data_high_risk_count

    llm_summary = summarize_paper_overall(
        evidence=evidence,
        risk_score=risk_score,
        risk_level=level,
        api_key=api_key,
        llm_model_name=llm_model_name,
    )

    llm_level = _normalize_risk_level(llm_summary.get("risk_level"))
    final_level = _max_risk_level(level, llm_level)
    llm_summary_is_consistent = _risk_rank(llm_level) >= _risk_rank(level)
    summary = llm_summary.get("summary") if llm_summary_is_consistent else ""

    return {
        "risk_score": risk_score,
        "risk_level": final_level,
        "summary": summary or conclusion,
        "key_concerns": llm_summary.get("key_concerns") or [],
        "suggestions": llm_summary.get("suggestions") or [],
        "evidence": evidence,
        "summary_source": "llm_prompt" if summary else "rule_based",
    }


def _risk_level_from_score(risk_score):
    if risk_score >= 70:
        return "high"
    if risk_score >= 40:
        return "medium"
    return "low"


def _minimum_risk_level_from_evidence(*, confirmed_count, reference_high_risk_count, data_high_risk_count=0):
    if confirmed_count >= 3 or data_high_risk_count >= 2:
        return "high"
    if confirmed_count >= 2 and reference_high_risk_count >= 1:
        return "high"
    if confirmed_count >= 1 or reference_high_risk_count >= 1 or data_high_risk_count >= 1:
        return "medium"
    return "low"


def _align_score_with_level(risk_score, risk_level):
    if risk_level == "high":
        return max(risk_score, 70)
    if risk_level == "medium":
        return max(risk_score, 40)
    return risk_score


def _normalize_risk_level(value):
    normalized = str(value or "").strip().lower()
    return normalized if normalized in {"low", "medium", "high"} else "low"


def _risk_rank(level):
    return {"low": 0, "medium": 1, "high": 2}.get(level, 0)


def _max_risk_level(*levels):
    return max((_normalize_risk_level(level) for level in levels), key=_risk_rank)


def _rule_based_conclusion(level, confirmed_count, reference_high_risk_count, data_high_risk_count=0):
    if level == "high":
        return (
            "论文存在高风险证据，建议优先人工复核确认 AI 段落、核验高风险引用，"
            "并在处置前保留原文与检测记录。"
        )
    if level == "medium":
        if confirmed_count or reference_high_risk_count or data_high_risk_count:
            return "论文存在明确风险证据，建议重点复核确认 AI 段落、参考文献和数据真实性。"
        return "论文存在中等风险段落，建议重点复核高概率段落与关键参考文献。"
    return "论文整体风险较低，但仍建议抽样复核可疑段落。"
