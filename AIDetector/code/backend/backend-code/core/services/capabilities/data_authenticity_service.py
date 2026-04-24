import re


_NUMBER_PATTERN = re.compile(r"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>%|％)?")
_CLAIM_KEYWORDS = ("显著", "证明", "表明", "提升", "降低", "优于", "有效")


def evaluate_data_authenticity(paragraph_results):
    findings = []
    metric_registry = {}

    for item in paragraph_results or []:
        paragraph_index = int(item.get("paragraph_index", 0))
        text = (item.get("text") or "").strip()
        if not text:
            continue

        for match in _NUMBER_PATTERN.finditer(text):
            value = float(match.group("value"))
            unit = match.group("unit")
            claim = _extract_claim_snippet(text, match.start(), match.end())
            metric_key = _normalize_metric_key(claim)

            risk_level = None
            reason = None
            evidence = f"value={value}, unit={'percent' if unit else 'number'}"

            if unit and (value < 0 or value > 100):
                risk_level = "high"
                reason = "百分比超出 0-100 的常识区间。"
            elif metric_key in metric_registry and abs(metric_registry[metric_key] - value) > 20:
                risk_level = "medium"
                reason = "同类指标在文档中出现较大数值跳变，存在口径不一致风险。"
            elif any(keyword in text for keyword in _CLAIM_KEYWORDS) and not _contains_statistical_evidence(text):
                risk_level = "low"
                reason = "包含强结论表达，但缺少显著性或样本量等统计支撑。"

            metric_registry[metric_key] = value

            if risk_level:
                findings.append(
                    {
                        "paragraph_index": paragraph_index,
                        "claim_text": claim,
                        "risk_level": risk_level,
                        "reason": reason,
                        "evidence": evidence,
                    }
                )

    summary = _build_summary(findings)
    return {
        "summary": summary,
        "findings": findings,
    }


def _extract_claim_snippet(text, start, end, window=32):
    left = max(0, start - window)
    right = min(len(text), end + window)
    return text[left:right].strip()


def _normalize_metric_key(claim_text):
    tokens = re.findall(r"[A-Za-z\u4e00-\u9fff]+", claim_text or "")
    if not tokens:
        return "unknown_metric"
    return "_".join(tokens[:4]).lower()


def _contains_statistical_evidence(text):
    lowered = (text or "").lower()
    return any(token in lowered for token in ("p<", "p =", "ci", "n=", "样本", "置信区间"))


def _build_summary(findings):
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
