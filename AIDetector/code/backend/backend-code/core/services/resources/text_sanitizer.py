def sanitize_text_content(value):
    if not isinstance(value, str):
        return value

    cleaned_chars = []
    for char in value:
        codepoint = ord(char)
        if char in {"\n", "\r", "\t"} or codepoint >= 32:
            cleaned_chars.append(char)
    return "".join(cleaned_chars)


def sanitize_json_like(value):
    if isinstance(value, str):
        return sanitize_text_content(value)
    if isinstance(value, list):
        return [sanitize_json_like(item) for item in value]
    if isinstance(value, dict):
        return {
            sanitize_text_content(str(key)): sanitize_json_like(item)
            for key, item in value.items()
        }
    return value
