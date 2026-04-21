import re


def analyze_review_relevance(*, review_segments, paper_segments):
    paper_entries = [
        {
            "paragraph_index": index,
            "text": text,
            "tokens": _tokenize(text),
        }
        for index, text in enumerate(paper_segments)
    ]
    results = []
    for review_index, review_text in enumerate(review_segments):
        review_tokens = _tokenize(review_text)
        best_match = None
        best_overlap = set()
        for paper_entry in paper_entries:
            overlap = review_tokens & paper_entry["tokens"]
            if best_match is None or len(overlap) > len(best_overlap):
                best_match = paper_entry
                best_overlap = overlap

        score = _overlap_score(review_tokens, best_overlap)
        results.append(
            {
                "review_paragraph_index": review_index,
                "review_text": review_text,
                "paper_paragraph_index": best_match["paragraph_index"] if best_match else None,
                "paper_text": best_match["text"] if best_match else "",
                "relevance_score": score,
                "label": "relevant" if score >= 0.2 else "weak_match",
                "explanation": _build_explanation(best_match, best_overlap, score),
            }
        )
    return results


def _tokenize(text):
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text or "")
        if len(token) >= 2
    }


def _overlap_score(review_tokens, overlap_tokens):
    if not review_tokens:
        return 0.0
    return round(len(overlap_tokens) / len(review_tokens), 4)


def _build_explanation(best_match, overlap_tokens, score):
    if best_match is None:
        return "No matching paper paragraph was found."
    if not overlap_tokens:
        return "The review paragraph has little lexical overlap with the paper paragraph."
    return (
        f"Matched paper paragraph #{best_match['paragraph_index']} with "
        f"{len(overlap_tokens)} shared terms and relevance score {score:.2f}."
    )
