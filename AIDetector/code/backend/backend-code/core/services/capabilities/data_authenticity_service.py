from .llm import assess_data_authenticity_finding


def evaluate_data_authenticity(paragraph_results, *, tables=None, api_key=None, llm_model_name=None):
    findings = []
    table_results = []
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
            llm_model_name=llm_model_name,
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
                    "source_type": "paragraph",
                    "claim_text": text[:240],
                    "risk_level": llm_finding["risk_level"],
                    "reason": llm_finding["reason"],
                    "evidence": text[:240],
                    "analysis_source": "llm",
                }
            )

    for table in tables or []:
        table_result, table_invoked, table_error = _evaluate_table_authenticity(
            table,
            api_key=api_key,
            llm_model_name=llm_model_name,
        )
        if table_error and llm_error is None:
            llm_error = table_error
        llm_invoked = llm_invoked or table_invoked
        if table_result:
            table_results.append(table_result)
            if table_result.get("risk_level") in {"low", "medium", "high"}:
                findings.append(
                    {
                        "source_type": "table",
                        "table_index": table_result.get("table_index"),
                        "claim_text": table_result.get("claim_text", ""),
                        "risk_level": table_result["risk_level"],
                        "reason": table_result.get("reason", ""),
                        "evidence": table_result.get("evidence", ""),
                        "analysis_source": table_result.get("analysis_source", "llm"),
                    }
                )

    summary = _build_summary(findings, llm_invoked=llm_invoked, llm_error=llm_error)
    return {
        "summary": summary,
        "findings": findings,
        "table_results": table_results,
    }


def _evaluate_table_authenticity(table, *, api_key=None, llm_model_name=None):
    if not isinstance(table, dict):
        return None, False, None
    text = (table.get("text") or "").strip()
    if not text:
        return None, False, None

    table_index = int(table.get("table_index") or 0)
    claim_text = f"Table {table_index + 1}: {text[:700]}"
    llm_finding = assess_data_authenticity_finding(
        paragraph_index=table_index,
        claim_text=claim_text,
        evidence=text[:900],
        api_key=api_key,
        llm_model_name=llm_model_name,
    )
    if isinstance(llm_finding, dict) and llm_finding.get("error"):
        return None, False, str(llm_finding.get("error") or "").strip()
    if not isinstance(llm_finding, dict):
        return None, False, None

    risk_level = llm_finding.get("risk_level")
    if risk_level not in {"none", "low", "medium", "high"}:
        return None, True, None

    return {
        "table_index": table_index,
        "source": table.get("source"),
        "page_number": table.get("page_number"),
        "row_count": table.get("row_count"),
        "column_count": table.get("column_count"),
        "headers": table.get("headers") or [],
        "risk_level": risk_level,
        "reason": llm_finding.get("reason", ""),
        "claim_text": claim_text[:240],
        "evidence": text[:900],
        "analysis_source": "llm",
    }, True, None


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
