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
  "risk_level": "none|low|medium|high",
  "reason": "string, 不超过100字"
}}
""".strip()


DATA_TABLE_AUTH_SYSTEM_PROMPT = (
    "你是学术论文表格数据真实性分析助手。请严格基于结构化表头、表项和上下文，"
    "判断表格中的数值、趋势或结论是否存在明显异常、过度完美、内部矛盾或缺少支撑的问题。"
    "只输出JSON。"
)


DATA_TABLE_AUTH_USER_TEMPLATE = """
输入表格：
- table_index: {table_index}
- source: {source}
- page_number: {page_number}
- row_count: {row_count}
- column_count: {column_count}
- headers_json: {headers_json}
- rows_json: {rows_json}
- text_preview: {text_preview}

请输出JSON：
{{
  "risk_level": "none|low|medium|high",
  "reason": "string, 不超过120字，说明依据的是哪些表头或表项",
  "evidence_summary": "string, 不超过160字，概括关键数值/趋势证据",
  "suspicious_cells": ["string, 可疑单元格或行列说明"]
}}
""".strip()


DATA_AUTH_SUMMARY_SYSTEM_PROMPT = (
    "你是学术论文数据真实性分析报告助手。请基于段落数据声明和表格分析结果，"
    "生成简短、克制、可复核的总体摘要。只输出JSON。"
)


DATA_AUTH_SUMMARY_USER_TEMPLATE = """
输入：
- analyzed_paragraph_count: {analyzed_paragraph_count}
- table_count: {table_count}
- analyzed_table_count: {analyzed_table_count}
- findings_json: {findings_json}
- table_results_json: {table_results_json}

请输出JSON：
{{
  "risk_level": "none|low|medium|high",
  "summary": "string, 不超过160字",
  "key_points": ["string, string"]
}}
""".strip()


REVIEW_ANALYSIS_SYSTEM_PROMPT = (
    "你是学术同行评审审查助手。请同时结合论文与Review内容，判断Review是否模板化、是否存在错误，"
    "以及Review与论文的相关度。只输出JSON。"
)


REVIEW_ANALYSIS_USER_TEMPLATE = """
输入：
- paper_text: {paper_text}
- review_paragraphs: {review_paragraphs}

请输出JSON：
{{
  "overall": {{
    "template_like_level": "low|medium|high",
    "wrongness_level": "low|medium|high",
    "relevance_level": "low|medium|high",
    "summary": "string, 不超过160字",
    "key_findings": ["string", "string"],
    "suggestions": ["string", "string"]
  }},
  "paragraph_results": [
    {{
      "review_paragraph_index": 0,
      "paper_paragraph_index": 0,
      "template_like_level": "low|medium|high",
      "wrongness_level": "low|medium|high",
      "relevance_score": "0到1的小数",
      "relevance_level": "low|medium|high",
      "explanation": "string, 不超过120字"
    }}
  ]
}}
""".strip()


def render_prompt(template, **kwargs):
    return template.format(**kwargs)
