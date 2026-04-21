from ..integrations import explain_text_segment


def build_suspicious_paragraph_explanations(paragraph_results, *, api_key=None, suspicious_threshold=0.5):
    explanations = []
    for result in paragraph_results:
        if float(result.get("probability", 0) or 0) < suspicious_threshold:
            continue
        explanations.append(
            {
                "paragraph_index": result["paragraph_index"],
                "text": result["text"],
                "probability": result["probability"],
                "explanation": explain_text_segment(
                    text=result["text"],
                    score=float(result["probability"]),
                    api_key=api_key,
                ),
            }
        )
    return explanations
