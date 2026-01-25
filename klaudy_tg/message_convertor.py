import telegramify_markdown


# Split by \n or space to strings <4096 symbols len
def markdown_and_split_text(text, max_len):
    text = telegramify_markdown.markdownify(
        text,
        max_line_length=None,
        normalize_whitespace=False
    )
    parts = []

    while len(text) > max_len:
        chunk = text[:max_len]

        split_pos = chunk.rfind('\n')

        if split_pos == -1:
            split_pos = chunk.rfind(' ')

        if split_pos == -1:
            split_pos = max_len

        parts.append(text[:split_pos].rstrip())
        text = text[split_pos:].lstrip()

    if text:
        parts.append(text)

    return parts
