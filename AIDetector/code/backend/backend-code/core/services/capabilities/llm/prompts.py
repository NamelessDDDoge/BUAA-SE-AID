SEGMENT_EXPLANATION_SYSTEM_PROMPT = (
    "你是学术论文鉴伪助手。请根据输入段落与AIGC概率，输出简洁、可执行的鉴伪理由。"
    "仅输出JSON，不要输出额外解释。"
)


SEGMENT_EXPLANATION_USER_TEMPLATE = """
输入信息：
- 段落文本：{text}
- AIGC概率：{score:.4f}

请输出JSON：
{{
  "explanation": "string, 不超过120字，说明为何可疑/为何偏人工",
  "evidence_points": ["string", "string"],
  "review_action": "string, 给审稿人的下一步建议"
}}
""".strip()


OVERALL_EVALUATION_SYSTEM_PROMPT = (
    "你是学术AI鉴伪系统的报告总结器。请基于输入统计信息输出整篇论文风险评价。"
    "仅输出JSON，不要输出额外文本。"
)


OVERALL_EVALUATION_USER_TEMPLATE = """
输入统计：
- total_paragraphs: {total_paragraphs}
- suspicious_paragraphs: {suspicious_paragraphs}
- confirmed_ai_paragraphs: {confirmed_ai_paragraphs}
- high_risk_references: {high_risk_references}
- high_risk_data_findings: {high_risk_data_findings}
- rule_based_risk_score: {risk_score}
- rule_based_risk_level: {risk_level}

请输出JSON：
{{
  "risk_level": "low|medium|high",
  "summary": "string, 不超过140字",
  "key_concerns": ["string", "string"],
  "suggestions": ["string", "string"]
}}
""".strip()


REFERENCE_AUTH_SYSTEM_PROMPT = (
    "你是学术参考文献真实性分析助手。请对单条参考文献给出真实性风险判断。"
    "只输出JSON。"
)


REFERENCE_AUTH_USER_TEMPLATE = """
输入：
- reference: {reference}

请输出JSON：
{{
  "authenticity_score": "0到1的小数",
  "authenticity_label": "likely_authentic|uncertain|high_risk|missing",
  "authenticity_reason": "string, 不超过120字"
}}
""".strip()


DATA_AUTH_SYSTEM_PROMPT = (
    "你是学术论文数据真实性分析助手。请根据可疑数据声明评估风险等级。"
    "只输出JSON。"
)


DATA_AUTH_USER_TEMPLATE = """
输入：
- paragraph_index: {paragraph_index}
- claim_text: {claim_text}
- evidence: {evidence}

请输出JSON：
{{
  "risk_level": "low|medium|high",
  "reason": "string, 不超过100字"
}}
""".strip()


def render_prompt(template, **kwargs):
    return template.format(**kwargs)
