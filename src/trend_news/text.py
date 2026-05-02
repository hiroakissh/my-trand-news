from __future__ import annotations

import html
import re
from html.parser import HTMLParser


_WHITESPACE_RE = re.compile(r"\s+")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def clean_text(value: str | None, *, max_length: int | None = None) -> str:
    if not value:
        return ""
    value = html.unescape(str(value))
    value = strip_html(value)
    value = _WHITESPACE_RE.sub(" ", value).strip()
    if max_length and len(value) > max_length:
        return value[: max_length - 1].rstrip() + "…"
    return value


def strip_html(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    text = parser.get_text()
    return text if text else value
