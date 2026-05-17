from .llm import analyze_review_text
from .llm.openai_client import get_llm_runtime_config


MAX_PAPER_TEXT_CHARS = 12000
MAX_REVIEW_PARAGRAPHS = 18
MAX_REVIEW_PARAGRAPH_CHARS = 800


def build_review_qualification(overall, paragraph_results=None):
    overall = overall if isinstance(overall, dict) else {}
    paragraph_results = paragraph_results if isinstance(paragraph_results, list) else []

    if overall.get("source") == "api_unavailable":
        return {
            "qualification_label": "unavailable",
            "qualification_text": "分析不可用",
            "is_qualified": None,
            "qualification_reason": "Review 分析服务不可用，无法给出合格性结论。",
            "failed_checks": [],
            "attention_checks": ["analysis_unavailable"],
        }

    failed_checks = []
    attention_checks = []

    template_level = _normalize_level(overall.get("template_like_level"))
    wrongness_level = _normalize_level(overall.get("wrongness_level"))
    relevance_level = _normalize_relevance_level(overall.get("relevance_level"))

    _collect_level_check(
        failed_checks,
        attention_checks,
        name="template_like",
        level=template_level,
        high_is_failure=True,
    )
    _collect_level_check(
        failed_checks,
        attention_checks,
        name="wrongness",
        level=wrongness_level,
        high_is_failure=True,
    )
    _collect_relevance_check(failed_checks, attention_checks, relevance_level)

    for item in paragraph_results:
        if not isinstance(item, dict):
            continue
        paragraph_prefix = f"paragraph_{item.get('review_paragraph_index', item.get('paragraph_index', 'unknown'))}"
        _collect_level_check(
            failed_checks,
            attention_checks,
            name=f"{paragraph_prefix}_template_like",
            level=_normalize_level(item.get("template_like_level")),
            high_is_failure=True,
        )
        _collect_level_check(
            failed_checks,
            attention_checks,
            name=f"{paragraph_prefix}_wrongness",
            level=_normalize_level(item.get("wrongness_level")),
            high_is_failure=True,
        )
        paragraph_relevance = _normalize_relevance_level(item.get("relevance_level"))
        relevance_score = _coerce_float(item.get("relevance_score"))
        if relevance_score is not None and relevance_score < 0.45:
            failed_checks.append(f"{paragraph_prefix}_relevance_score_low")
        elif relevance_score is not None and relevance_score < 0.65:
            attention_checks.append(f"{paragraph_prefix}_relevance_score_medium")
        _collect_relevance_check(failed_checks, attention_checks, paragraph_relevance, prefix=paragraph_prefix)

    failed_checks = _dedupe_checks(failed_checks)
    attention_checks = _dedupe_checks(attention_checks)

    if failed_checks:
        return {
            "qualification_label": "unqualified",
            "qualification_text": "不合格",
            "is_qualified": False,
            "qualification_reason": "存在高模板化、高错误风险或低相关度证据，不应判定为合格 Review。",
            "failed_checks": failed_checks,
            "attention_checks": attention_checks,
        }

    if attention_checks:
        return {
            "qualification_label": "attention",
            "qualification_text": "需关注",
            "is_qualified": False,
            "qualification_reason": "未发现直接不合格因素，但存在中等模板化、错误风险或相关度一般的情况，建议人工复核。",
            "failed_checks": [],
            "attention_checks": attention_checks,
        }

    return {
        "qualification_label": "qualified",
        "qualification_text": "合格",
        "is_qualified": True,
        "qualification_reason": "模板化倾向低、内容错误风险低，且与论文相关度达到中高水平。",
        "failed_checks": [],
        "attention_checks": [],
    }


def evaluate_review_analysis(*, paper_document, review_document, api_key=None, llm_model_name=None):
    review_paragraphs = [
        {
            "review_paragraph_index": index,
            "text": str(paragraph or "")[:MAX_REVIEW_PARAGRAPH_CHARS],
        }
        for index, paragraph in enumerate(review_document.get("paragraphs") or [])
        if str(paragraph or "").strip()
    ][:MAX_REVIEW_PARAGRAPHS]

    llm_result = analyze_review_text(
        paper_text=(paper_document.get("text_content") or "")[:MAX_PAPER_TEXT_CHARS],
        review_paragraphs=review_paragraphs,
        api_key=api_key,
        timeout=60,
        llm_model_name=llm_model_name,
    )
    if isinstance(llm_result, dict) and llm_result.get("error"):
        suggestion = llm_result.get("error")
        overall = {
            "template_like_level": "unknown",
            "wrongness_level": "unknown",
            "relevance_level": "unknown",
            "summary": "Review 分析暂时不可用。",
            "key_findings": [],
            "suggestions": [suggestion],
            "source": "api_unavailable",
        }
        return {
            "overall": {**overall, **build_review_qualification(overall)},
            "paragraph_results": [],
        }
    elif not isinstance(llm_result, dict):
        runtime_config = get_llm_runtime_config(api_key=api_key)
        suggestion = llm_result.get("error") if isinstance(llm_result, dict) else None
        if not suggestion:
            if not runtime_config.get("endpoint") or not runtime_config.get("key"):
                suggestion = "请先配置对话模型的 endpoint 和 API key（OPENAI_COMPAT_* 或 FASTDETECT_OPENAI_COMPAT_*）。"
            else:
                suggestion = "请检查 LLM 接口连通性或返回的 JSON 格式。"
        overall = {
            "template_like_level": "unknown",
            "wrongness_level": "unknown",
            "relevance_level": "unknown",
            "summary": "Review 分析暂时不可用。",
            "key_findings": [],
            "suggestions": [suggestion],
            "source": "api_unavailable",
        }
        return {
            "overall": {**overall, **build_review_qualification(overall)},
            "paragraph_results": [],
        }

    paragraph_results = [
        {**item, "analysis_source": "llm"}
        for item in llm_result.get("paragraph_results", [])
    ]
    overall = {**llm_result.get("overall", {}), "source": "llm"}
    return {
        "overall": {**overall, **build_review_qualification(overall, paragraph_results)},
        "paragraph_results": paragraph_results,
    }


def _normalize_level(value):
    level = str(value or "").strip().lower()
    return level if level in {"low", "medium", "high"} else "unknown"


def _normalize_relevance_level(value):
    level = str(value or "").strip().lower()
    if level in {"high", "relevant"}:
        return "high"
    if level in {"medium"}:
        return "medium"
    if level in {"low", "weak_match"}:
        return "low"
    return "unknown"


def _collect_level_check(failed_checks, attention_checks, *, name, level, high_is_failure):
    if high_is_failure and level == "high":
        failed_checks.append(f"{name}_high")
    elif level == "medium":
        attention_checks.append(f"{name}_medium")
    elif level == "unknown":
        attention_checks.append(f"{name}_unknown")


def _collect_relevance_check(failed_checks, attention_checks, level, prefix="overall"):
    if level == "low":
        failed_checks.append(f"{prefix}_relevance_low")
    elif level == "medium":
        attention_checks.append(f"{prefix}_relevance_medium")
    elif level == "unknown":
        attention_checks.append(f"{prefix}_relevance_unknown")


def _coerce_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe_checks(checks):
    return list(dict.fromkeys(checks))
