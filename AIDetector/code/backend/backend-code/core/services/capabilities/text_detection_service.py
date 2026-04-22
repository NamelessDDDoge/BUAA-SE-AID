from .llm import detect_text_segment


def analyze_text_segments(segments, *, api_key=None, suspicious_threshold=0.5):
    results = []
    for index, segment in enumerate(segments):
        probability, details = _detect_segment_probability(segment, api_key=api_key)
        results.append(
            {
                "paragraph_index": index,
                "text": segment,
                "probability": probability,
                "label": "suspicious" if probability >= suspicious_threshold else "clean",
                "details": details,
            }
        )
    return results


def _detect_segment_probability(segment, *, api_key=None):
    try:
        response_data = detect_text_segment(segment, api_key=api_key)
        payload = response_data.get("data", {})
        probability = float(payload.get("prob", 0) or 0)
        details = payload.get("details", {})
    except Exception as exc:
        probability = 0.0
        details = {"error": str(exc)}
    return probability, details
