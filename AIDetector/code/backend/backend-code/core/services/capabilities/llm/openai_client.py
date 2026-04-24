import json
import os

import requests

from .prompts import (
    DATA_AUTH_SYSTEM_PROMPT,
    DATA_AUTH_USER_TEMPLATE,
    OVERALL_EVALUATION_SYSTEM_PROMPT,
    OVERALL_EVALUATION_USER_TEMPLATE,
    REFERENCE_AUTH_SYSTEM_PROMPT,
    REFERENCE_AUTH_USER_TEMPLATE,
    SEGMENT_EXPLANATION_SYSTEM_PROMPT,
    SEGMENT_EXPLANATION_USER_TEMPLATE,
    render_prompt,
)


DEFAULT_LLM_ENDPOINT = os.environ.get("OPENAI_COMPAT_ENDPOINT", "").strip()
DEFAULT_LLM_MODEL = os.environ.get("OPENAI_COMPAT_MODEL", "gpt-4o-mini")
DEFAULT_LLM_API_KEY = os.environ.get("OPENAI_COMPAT_API_KEY", "").strip()


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
        return None

    risk_level = str(response_json.get("risk_level") or "").strip().lower()
    reason = str(response_json.get("reason") or "").strip()
    if risk_level not in {"low", "medium", "high"}:
        return None
    return {
        "risk_level": risk_level,
        "reason": reason or "LLM 未返回原因说明。",
    }


def _request_structured_json(*, system_prompt, user_prompt, api_key=None, timeout=30):
    endpoint = DEFAULT_LLM_ENDPOINT
    key = (api_key or DEFAULT_LLM_API_KEY or "").strip()
    if not endpoint or not key:
        return None

    try:
        payload = {
            "model": DEFAULT_LLM_MODEL,
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
        body = response.json()
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return None
        return _extract_json(content)
    except Exception:
        return None


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
