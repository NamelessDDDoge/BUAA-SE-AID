from .llm import analyze_review_text
from .llm.openai_client import get_llm_runtime_config


MAX_PAPER_TEXT_CHARS = 12000
MAX_REVIEW_PARAGRAPHS = 18
MAX_REVIEW_PARAGRAPH_CHARS = 800


def evaluate_review_analysis(*, paper_document, review_document, api_key=None):
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
    )
    if isinstance(llm_result, dict) and llm_result.get("error"):
        suggestion = llm_result.get("error")
        return {
            "overall": {
                "template_like_level": "low",
                "wrongness_level": "low",
                "relevance_level": "low",
                "summary": "Review 分析暂时不可用。",
                "key_findings": [],
                "suggestions": [suggestion],
                "source": "api_unavailable",
            },
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
        return {
            "overall": {
                "template_like_level": "low",
                "wrongness_level": "low",
                "relevance_level": "low",
                "summary": "Review 分析暂时不可用。",
                "key_findings": [],
                "suggestions": [suggestion],
                "source": "api_unavailable",
            },
            "paragraph_results": [],
        }

    return {
        "overall": {**llm_result.get("overall", {}), "source": "llm"},
        "paragraph_results": [
            {**item, "analysis_source": "llm"}
            for item in llm_result.get("paragraph_results", [])
        ],
    }