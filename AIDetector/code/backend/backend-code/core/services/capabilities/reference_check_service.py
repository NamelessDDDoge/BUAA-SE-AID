import re


def evaluate_references(*, text_content, references):
    normalized_body = _normalize_tokens(text_content)
    results = []
    for index, reference in enumerate(references):
        reference_tokens = _normalize_tokens(reference)
        overlap = len(normalized_body & reference_tokens)
        results.append(
            {
                "reference_index": index,
                "reference": reference,
                "exists": bool(reference.strip()),
                "is_relevant": overlap > 0,
                "overlap_terms": sorted(normalized_body & reference_tokens)[:10],
            }
        )
    return results


def _normalize_tokens(text):
    return {
        token
        for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text or "")
        if len(token) >= 2
    }
