from .llm import assess_data_authenticity_finding, assess_table_authenticity, summarize_data_authenticity


def evaluate_data_authenticity(paragraph_results, *, tables=None, api_key=None, llm_model_name=None):
    findings = []
    table_results = []
    llm_invoked = False
    llm_error = None
    analyzed_paragraph_count = 0
    for item in paragraph_results or []:
        paragraph_index = int(item.get("paragraph_index", 0))
        text = (item.get("text") or "").strip()
        if not text:
            continue
        analyzed_paragraph_count += 1

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

    summary_error = None
    llm_summary = None
    has_analyzable_content = analyzed_paragraph_count > 0 or bool(tables)
    if has_analyzable_content:
        llm_summary = summarize_data_authenticity(
            findings=findings,
            table_results=table_results,
            analyzed_paragraph_count=analyzed_paragraph_count,
            table_count=len(tables or []),
            api_key=api_key,
            llm_model_name=llm_model_name,
        )
    if isinstance(llm_summary, dict) and llm_summary.get("error"):
        summary_error = str(llm_summary.get("error") or "").strip()
    elif isinstance(llm_summary, dict) and llm_summary.get("summary"):
        llm_invoked = True
        return {
            "summary": llm_summary["summary"],
            "summary_source": "llm",
            "summary_risk_level": llm_summary.get("risk_level", "none"),
            "summary_key_points": llm_summary.get("key_points", []),
            "findings": findings,
            "table_results": table_results,
            "llm_error": llm_error,
        }

    summary = _build_summary(findings, llm_invoked=llm_invoked, llm_error=llm_error)
    return {
        "summary": summary,
        "summary_source": "rule_based",
        "summary_risk_level": _infer_summary_risk_level(findings),
        "summary_key_points": [],
        "findings": findings,
        "table_results": table_results,
        "llm_error": llm_error,
        "summary_error": summary_error,
    }


def _evaluate_table_authenticity(table, *, api_key=None, llm_model_name=None):
    if not isinstance(table, dict):
        return None, False, None
    text = (table.get("text") or "").strip()
    if not text:
        return None, False, None

    table_index = int(table.get("table_index") or 0)
    llm_finding = assess_table_authenticity(
        table=table,
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
        "rows_preview": (table.get("rows") or [])[:5],
        "risk_level": risk_level,
        "reason": llm_finding.get("reason", ""),
        "claim_text": _build_table_claim_text(table),
        "evidence": text[:900],
        "evidence_summary": llm_finding.get("evidence_summary", ""),
        "suspicious_cells": llm_finding.get("suspicious_cells", []),
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


def _infer_summary_risk_level(findings):
    levels = {item.get("risk_level") for item in findings or []}
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    if "low" in levels:
        return "low"
    return "none"


def _build_table_claim_text(table):
    headers = [str(item) for item in (table.get("headers") or []) if str(item).strip()]
    header_text = " | ".join(headers)
    prefix = f"Table {int(table.get('table_index') or 0) + 1}"
    if header_text:
        return f"{prefix} headers: {header_text}"[:240]
    return f"{prefix}: {str(table.get('text') or '')[:220]}"
