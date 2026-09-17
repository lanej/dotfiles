from textkit.core import normalize_newlines


def test_normalize_newlines_handles_crlf_and_cr():
    assert normalize_newlines("a\r\nb\rc\nd") == "a\nb\nc\nd"
