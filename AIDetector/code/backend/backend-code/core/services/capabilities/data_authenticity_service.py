from .llm import assess_data_authenticity_finding


def evaluate_data_authenticity(paragraph_results, api_key=None):
    findings = []
    llm_invoked = False
    llm_error = None
    for item in paragraph_results or []:
        paragraph_index = int(item.get("paragraph_index", 0))
        text = (item.get("text") or "").strip()
        if not text:
            continue

        llm_finding = assess_data_authenticity_finding(
            paragraph_index=paragraph_index,
            claim_text=text,
            evidence=text[:240],
            api_key=api_key,
        )
        if isinstance(llm_finding, dict) and llm_finding.get("error"):
            if llm_error is None:
                llm_error = str(llm_finding.get("error") or "").strip()
            continue
        if isinstance(llm_finding, dict):
            llm_invoked = True
        if isinstance(llm_finding, dict) and llm_finding.get("risk_level") in {"low", "medium", "high"}:
            findings.append(
                {
                    "paragraph_index": paragraph_index,
                    "claim_text": text[:240],
                    "risk_level": llm_finding["risk_level"],
                    "reason": llm_finding["reason"],
                    "evidence": text[:240],
                    "analysis_source": "llm",
                }
            )

    summary = _build_summary(findings, llm_invoked=llm_invoked, llm_error=llm_error)
    return {
        "summary": summary,
        "findings": findings,
    }


def _build_summary(findings, llm_invoked=False, llm_error=None):
    if llm_error:
        return f"数据真实性分析调用 LLM 失败：{llm_error}"
    if not llm_invoked:
        return "数据真实性分析未能调用 LLM。"
    if not findings:
        return "未发现明显数据一致性风险。"

    level_weight = {"high": 3, "medium": 2, "low": 1}
    weighted_score = sum(level_weight.get(item.get("risk_level"), 0) for item in findings)
    high_count = sum(1 for item in findings if item.get("risk_level") == "high")

    if high_count > 0:
        overall = "高风险"
    elif weighted_score >= 8:
        overall = "中风险"
    else:
        overall = "低风险"

    return f"共发现 {len(findings)} 项数据可疑点，综合判定为{overall}。"
