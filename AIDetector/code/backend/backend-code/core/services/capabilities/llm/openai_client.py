import json
import os

import requests

from .prompts import (
    DATA_AUTH_SYSTEM_PROMPT,
    DATA_AUTH_USER_TEMPLATE,
    OVERALL_EVALUATION_SYSTEM_PROMPT,
    OVERALL_EVALUATION_USER_TEMPLATE,
    REVIEW_ANALYSIS_SYSTEM_PROMPT,
    REVIEW_ANALYSIS_USER_TEMPLATE,
    REFERENCE_AUTH_SYSTEM_PROMPT,
    REFERENCE_AUTH_USER_TEMPLATE,
    SEGMENT_EXPLANATION_SYSTEM_PROMPT,
    SEGMENT_EXPLANATION_USER_TEMPLATE,
    render_prompt,
)


DEFAULT_LLM_ENDPOINT = os.environ.get("OPENAI_COMPAT_ENDPOINT", "").strip()
DEFAULT_LLM_MODEL = os.environ.get("OPENAI_COMPAT_MODEL", "gpt-4o-mini")
DEFAULT_LLM_API_KEY = os.environ.get("OPENAI_COMPAT_API_KEY", "").strip()


def get_llm_runtime_config(api_key=None):
    endpoint = (
        os.environ.get("OPENAI_COMPAT_ENDPOINT", "").strip()
        or os.environ.get("FASTDETECT_OPENAI_COMPAT_ENDPOINT", "").strip()
        or os.environ.get("FASTDETECT_LLM_ENDPOINT", "").strip()
        or DEFAULT_LLM_ENDPOINT
    )
    model = (
        os.environ.get("OPENAI_COMPAT_MODEL", "").strip()
        or os.environ.get("FASTDETECT_OPENAI_COMPAT_MODEL", "").strip()
        or DEFAULT_LLM_MODEL
        or "gpt-4o-mini"
    )
    key = (
        (api_key or "").strip()
        or os.environ.get("OPENAI_COMPAT_API_KEY", "").strip()
        or os.environ.get("FASTDETECT_OPENAI_COMPAT_API_KEY", "").strip()
        or DEFAULT_LLM_API_KEY
    )
    return {
        "endpoint": endpoint,
        "model": model,
        "key": key,
    }


def explain_text_segment(*, text, score, api_key=None):
    fallback = _fallback_segment_explanation(score)
    response_json = _request_structured_json(
        system_prompt=SEGMENT_EXPLANATION_SYSTEM_PROMPT,
        user_prompt=render_prompt(SEGMENT_EXPLANATION_USER_TEMPLATE, text=text, score=score),
        api_key=api_key,
    )
    if not isinstance(response_json, dict):
        return fallback

    explanation = str(response_json.get("explanation") or "").strip()
    if not explanation:
        return fallback
    return explanation


def summarize_paper_overall(*, evidence, risk_score, risk_level, api_key=None):
    fallback = {
        "risk_level": risk_level,
        "summary": _fallback_overall_summary(risk_level),
        "key_concerns": [],
        "suggestions": ["建议人工重点复核高风险段落与参考文献。"],
    }
    user_prompt = render_prompt(
        OVERALL_EVALUATION_USER_TEMPLATE,
        total_paragraphs=evidence.get("total_paragraphs", 0),
        suspicious_paragraphs=evidence.get("suspicious_paragraphs", 0),
        confirmed_ai_paragraphs=evidence.get("confirmed_ai_paragraphs", 0),
        high_risk_references=evidence.get("high_risk_references", 0),
        high_risk_data_findings=evidence.get("high_risk_data_findings", 0),
        risk_score=risk_score,
        risk_level=risk_level,
    )
    response_json = _request_structured_json(
        system_prompt=OVERALL_EVALUATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        api_key=api_key,
    )
    if not isinstance(response_json, dict):
        return fallback

    return {
        "risk_level": str(response_json.get("risk_level") or risk_level),
        "summary": str(response_json.get("summary") or fallback["summary"]),
        "key_concerns": _to_string_list(response_json.get("key_concerns")),
        "suggestions": _to_string_list(response_json.get("suggestions")),
    }


def assess_reference_authenticity(*, reference, api_key=None):
    response_json = _request_structured_json(
        system_prompt=REFERENCE_AUTH_SYSTEM_PROMPT,
        user_prompt=render_prompt(REFERENCE_AUTH_USER_TEMPLATE, reference=reference or ""),
        api_key=api_key,
    )
    if not isinstance(response_json, dict):
        return None

    score = _coerce_float(response_json.get("authenticity_score"))
    label = str(response_json.get("authenticity_label") or "").strip()
    reason = str(response_json.get("authenticity_reason") or "").strip()
    if score is None or not label:
        return None
    return {
        "authenticity_score": max(0.0, min(1.0, float(score))),
        "authenticity_label": label,
        "authenticity_reason": reason or "LLM 未返回原因说明。",
    }


def assess_data_authenticity_finding(*, paragraph_index, claim_text, evidence, api_key=None):
    response_json = _request_structured_json(
        system_prompt=DATA_AUTH_SYSTEM_PROMPT,
        user_prompt=render_prompt(
            DATA_AUTH_USER_TEMPLATE,
            paragraph_index=int(paragraph_index or 0),
            claim_text=claim_text or "",
            evidence=evidence or "",
        ),
        api_key=api_key,
    )
    if not isinstance(response_json, dict):
        if isinstance(response_json, str):
            return {"error": response_json}
        return None

    risk_level = str(response_json.get("risk_level") or "").strip().lower()
    reason = str(response_json.get("reason") or "").strip()
    if risk_level not in {"none", "low", "medium", "high"}:
        return None
    return {
        "risk_level": risk_level,
        "reason": reason or "LLM 未返回原因说明。",
    }


def analyze_review_text(*, paper_text, review_paragraphs, api_key=None, timeout=60):
    response_json = _request_structured_json(
        system_prompt=REVIEW_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=render_prompt(
            REVIEW_ANALYSIS_USER_TEMPLATE,
            paper_text=paper_text or "",
            review_paragraphs=_format_review_paragraphs(review_paragraphs),
        ),
        api_key=api_key,
        timeout=timeout,
    )
    if not isinstance(response_json, dict):
        if isinstance(response_json, str):
            return {"error": response_json}
        return None

    overall = response_json.get("overall") if isinstance(response_json.get("overall"), dict) else {}
    paragraph_results = response_json.get("paragraph_results") if isinstance(response_json.get("paragraph_results"), list) else []
    return {
        "overall": {
            "template_like_level": _normalize_level(overall.get("template_like_level")),
            "wrongness_level": _normalize_level(overall.get("wrongness_level")),
            "relevance_level": _normalize_level(overall.get("relevance_level")),
            "summary": str(overall.get("summary") or "暂无整体总结。"),
            "key_findings": _to_string_list(overall.get("key_findings")),
            "suggestions": _to_string_list(overall.get("suggestions")),
        },
        "paragraph_results": [
            {
                "review_paragraph_index": _coerce_int(item.get("review_paragraph_index")),
                "paper_paragraph_index": _coerce_optional_int(item.get("paper_paragraph_index")),
                "template_like_level": _normalize_level(item.get("template_like_level")),
                "wrongness_level": _normalize_level(item.get("wrongness_level")),
                "relevance_score": _coerce_float(item.get("relevance_score")),
                "relevance_level": _normalize_level(item.get("relevance_level")),
                "explanation": str(item.get("explanation") or ""),
            }
            for item in paragraph_results
            if isinstance(item, dict)
        ],
    }


def _request_structured_json(*, system_prompt, user_prompt, api_key=None, timeout=30):
    config = get_llm_runtime_config(api_key=api_key)
    endpoint = config["endpoint"]
    model = config["model"]
    key = config["key"]
    if not endpoint or not key:
        return (
            "LLM API endpoint 或 API key 未配置。"
            "请配置 OPENAI_COMPAT_*（或 FASTDETECT_OPENAI_COMPAT_*）环境变量。"
        )

    if endpoint.rstrip("/").endswith("/api/detect"):
        return (
            "当前 endpoint 指向 FastDetect 文本检测接口(/api/detect)，"
            "不是 OpenAI 兼容聊天接口。请改为聊天 completions endpoint。"
        )

    try:
        payload = {
            "model": model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = requests.post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        try:
            body = response.json()
        except Exception:
            return f"LLM 接口返回了非 JSON 响应，HTTP {response.status_code}。"
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return "LLM 接口返回内容为空。"
        parsed = _extract_json(content)
        if parsed is None:
            return f"LLM 返回内容不是可解析的 JSON：{content[:200]}"
        return parsed
    except requests.RequestException as exc:
        return f"LLM 请求失败：{exc}"
    except Exception as exc:
        return f"LLM 未知错误：{exc}"


def _extract_json(content):
    try:
        return json.loads(content)
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except Exception:
                return None
    return None


def _to_string_list(value):
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _coerce_float(value):
    try:
        return float(value)
    except Exception:
        return None


def _coerce_int(value):
    try:
        return int(value)
    except Exception:
        return None


def _coerce_optional_int(value):
    if value in (None, ""):
        return None
    return _coerce_int(value)


def _normalize_level(value):
    level = str(value or "").strip().lower()
    return level if level in {"low", "medium", "high"} else "low"


def _format_review_paragraphs(review_paragraphs):
    if not isinstance(review_paragraphs, list):
        return "[]"
    formatted = []
    for item in review_paragraphs:
        if not isinstance(item, dict):
            continue
        formatted.append({
            "review_paragraph_index": item.get("review_paragraph_index"),
            "text": str(item.get("text") or ""),
        })
    return json.dumps(formatted, ensure_ascii=False)


def _fallback_segment_explanation(score):
    return (
        "该段落被标记是因为生成文本概率较高。"
        if score >= 0.5
        else "该段落当前更接近人工写作风格。"
    )


def _fallback_overall_summary(risk_level):
    if risk_level == "high":
        return "整篇论文综合风险较高，建议优先进行人工复核与引用核验。"
    if risk_level == "medium":
        return "整篇论文存在中等风险，建议重点检查高概率段落与关键数据声明。"
    return "整篇论文总体风险较低，建议抽样复核。"
