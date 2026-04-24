import re

from .llm import assess_reference_authenticity


def evaluate_references(*, text_content, references, api_key=None):
    normalized_body = _normalize_tokens(text_content)
    results = []
    for index, reference in enumerate(references):
        reference_tokens = _normalize_tokens(reference)
        overlap = len(normalized_body & reference_tokens)
        authenticity = _evaluate_reference_authenticity(reference)
        llm_auth = assess_reference_authenticity(reference=reference, api_key=api_key)
        if isinstance(llm_auth, dict):
            authenticity = {
                "score": llm_auth.get("authenticity_score", authenticity["score"]),
                "label": llm_auth.get("authenticity_label", authenticity["label"]),
                "reason": llm_auth.get("authenticity_reason", authenticity["reason"]),
                "source": "llm",
            }
        else:
            authenticity = {
                **authenticity,
                "source": "rule_based",
            }
        results.append(
            {
                "reference_index": index,
                "reference": reference,
                "exists": bool(reference.strip()),
                "is_relevant": overlap > 0,
                "overlap_terms": sorted(normalized_body & reference_tokens)[:10],
                "authenticity_score": authenticity["score"],
                "authenticity_label": authenticity["label"],
                "authenticity_reason": authenticity["reason"],
                "analysis_source": authenticity["source"],
            }
        )
    return results


def _normalize_tokens(text):
    return {
        token
        for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text or "")
        if len(token) >= 2
    }


def _evaluate_reference_authenticity(reference):
    text = (reference or "").strip()
    if not text:
        return {
            "score": 0.0,
            "label": "missing",
            "reason": "参考文献为空或无法解析。",
        }

    checks = []
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    checks.append((0.25, bool(year_match), "包含合理年份"))

    doi_match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text, flags=re.IGNORECASE)
    checks.append((0.3, bool(doi_match), "包含 DOI"))

    author_like = bool(re.search(r"[A-Za-z\u4e00-\u9fff]+\s*(,|，|and|与)", text))
    checks.append((0.2, author_like, "包含作者信息"))

    has_title_like = len(text) >= 20
    checks.append((0.15, has_title_like, "具备标题长度特征"))

    has_source = bool(re.search(r"(Journal|Proceedings|会议|期刊|vol\.|no\.|pp\.)", text, flags=re.IGNORECASE))
    checks.append((0.1, has_source, "具备来源信息"))

    score = sum(weight for weight, passed, _ in checks if passed)
    missing_reasons = [label for _weight, passed, label in checks if not passed]

    if score >= 0.75:
        label = "likely_authentic"
        reason = "字段结构较完整。"
    elif score >= 0.4:
        label = "uncertain"
        reason = "部分关键字段缺失，真实性需人工复核。"
    else:
        label = "high_risk"
        reason = "关键字段明显不足，存在伪造或格式异常风险。"

    if missing_reasons:
        reason = f"{reason} 缺失项：{', '.join(missing_reasons[:3])}。"

    return {
        "score": round(float(score), 3),
        "label": label,
        "reason": reason,
    }
