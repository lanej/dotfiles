"""Small string helpers."""


def normalize_newlines(text):
    """Convert CRLF and CR line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")
