import re

def sanitize_for_telegram(text: str) -> str:
    """
    Sanitizes text to be compatible with Telegram's HTML parse mode.
    - Converts basic Markdown.
    - Replaces unsupported HTML tags with safe alternatives.
    """
    # Convert basic markdown that the AI might still use
    text = text.replace('**', '<b>').replace('**', '</b>')
    text = re.sub(r'(?<!<)/?\*(?!<)', '<i>', text, 1)
    text = text.replace('*', '</i>')

    # Replace <br> tags with newlines for proper line breaks
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    
    # Handle list tags gracefully
    text = re.sub(r'<ul>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</ul>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<li>', '\n• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '', text, flags=re.IGNORECASE)

    # Strip any remaining unsupported tags to prevent errors
    allowed_tags = ['b', 'i', 'u', 's', 'tg-spoiler', 'a', 'code', 'pre']
    text = re.sub(r'</?(?!(?:' + '|'.join(allowed_tags) + r'))\b[^>]*>', '', text, flags=re.IGNORECASE)
    
    return text.strip()