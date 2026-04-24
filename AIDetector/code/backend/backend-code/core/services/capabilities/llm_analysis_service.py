from .llm import explain_text_segment, summarize_paper_overall


def build_suspicious_paragraph_explanations(paragraph_results, *, api_key=None, suspicious_threshold=0.5):
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
                ),
            }
        )
    return explanations


def build_overall_paper_evaluation(
    *,
    paragraph_results,
    confirmed_ai_paragraphs,
    reference_results,
    data_authenticity_results,
    api_key=None,
):
    total_paragraphs = len(paragraph_results or [])
    suspicious_count = sum(1 for item in (paragraph_results or []) if item.get("label") == "suspicious")
    confirmed_count = len(confirmed_ai_paragraphs or [])
    reference_high_risk_count = sum(
        1
        for item in (reference_results or [])
        if item.get("authenticity_label") in {"high_risk", "missing"}
    )
    data_findings = (data_authenticity_results or {}).get("findings") or []
    data_high_risk_count = sum(1 for item in data_findings if item.get("risk_level") == "high")

    risk_score = 0
    if total_paragraphs > 0:
        risk_score += min(40, int((suspicious_count / total_paragraphs) * 40))
    risk_score += min(30, confirmed_count * 6)
    risk_score += min(15, reference_high_risk_count * 3)
    risk_score += min(15, data_high_risk_count * 5)

    if risk_score >= 70:
        level = "high"
        conclusion = "整篇论文存在较高 AI 生成与学术真实性风险，建议优先人工复核并进行来源核验。"
    elif risk_score >= 40:
        level = "medium"
        conclusion = "论文存在中等风险段落，建议重点复核高概率段落与关键参考文献。"
    else:
        level = "low"
        conclusion = "论文整体风险较低，但仍建议抽样复核可疑段落。"

    evidence = {
        "total_paragraphs": total_paragraphs,
        "suspicious_paragraphs": suspicious_count,
        "confirmed_ai_paragraphs": confirmed_count,
        "high_risk_references": reference_high_risk_count,
        "high_risk_data_findings": data_high_risk_count,
    }

    llm_summary = summarize_paper_overall(
        evidence=evidence,
        risk_score=risk_score,
        risk_level=level,
        api_key=api_key,
    )

    return {
        "risk_score": risk_score,
        "risk_level": llm_summary.get("risk_level") or level,
        "summary": llm_summary.get("summary") or conclusion,
        "key_concerns": llm_summary.get("key_concerns") or [],
        "suggestions": llm_summary.get("suggestions") or [],
        "evidence": evidence,
        "summary_source": "llm_prompt" if llm_summary.get("summary") else "rule_based",
    }
