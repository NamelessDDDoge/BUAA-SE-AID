def explain_text_segment(*, text, score, api_key=None):
    del api_key
    return (
        "This paragraph was flagged because its generated-text score "
        f"reached {score:.2f}. Review the wording for repeated phrasing, "
        "overly uniform structure, or unsupported claims."
    )
