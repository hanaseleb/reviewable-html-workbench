"""Small safe markdown subset renderer for plan previews."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from urllib.parse import urlparse


@dataclass(frozen=True)
class Section:
    heading_text: str
    heading_level: int
    body: str
    is_preamble: bool = False


_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.+)$")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)\s*([A-Za-z0-9_-]*)\s*$")


def split_sections(text: str) -> tuple[str, list[Section]]:
    """Split markdown into top-level sections without treating fenced headings as sections."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    title = ""
    start = 0
    first_nonblank = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first_nonblank is not None:
        heading = _match_heading(lines[first_nonblank])
        if heading is not None and heading[0] == 1 and all(not line.strip() for line in lines[:first_nonblank]):
            title = heading[1]
            start = first_nonblank + 1

    body_lines = lines[start:]
    headings = _heading_positions(body_lines)
    if not headings:
        body = "\n".join(body_lines).strip("\n")
        return title, [Section("", 2, body, is_preamble=True)] if body else []

    split_level = min(level for _, level, _ in headings)
    split_headings = [(index, level, heading_text) for index, level, heading_text in headings if level == split_level]
    sections: list[Section] = []
    first_heading_index = split_headings[0][0]
    preamble = "\n".join(body_lines[:first_heading_index]).strip("\n")
    if preamble:
        sections.append(Section("", split_level, preamble, is_preamble=True))

    for position, (line_index, level, heading_text) in enumerate(split_headings):
        next_index = split_headings[position + 1][0] if position + 1 < len(split_headings) else len(body_lines)
        body = "\n".join(body_lines[line_index + 1 : next_index]).strip("\n")
        sections.append(Section(heading_text, level, body))
    return title, sections


def to_html(markdown: str) -> str:
    """Render the supported markdown subset to escaped HTML."""

    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    html_parts: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        fence = _FENCE_RE.match(line)
        if fence:
            html, index = _render_code_fence(lines, index, fence.group(1), fence.group(2))
            html_parts.append(html)
            continue

        heading = _match_heading(line)
        if heading is not None:
            level, heading_text = heading
            tag = f"h{min(max(level, 2), 6)}"
            html_parts.append(f"<{tag}>{escape(heading_text)}</{tag}>")
            index += 1
            continue

        if _is_horizontal_rule(line):
            html_parts.append("<hr>")
            index += 1
            continue

        if _is_table_start(lines, index):
            html, index = _render_table(lines, index)
            html_parts.append(html)
            continue

        if _LIST_ITEM_RE.match(line):
            html, index = _render_list(lines, index)
            html_parts.append(html)
            continue

        if line.lstrip().startswith(">"):
            html, index = _render_blockquote(lines, index)
            html_parts.append(html)
            continue

        html, index = _render_paragraph(lines, index)
        html_parts.append(html)
    return "\n".join(html_parts)


def heading_texts(markdown: str) -> tuple[str, ...]:
    """Return normalized heading text found outside fenced code blocks."""

    headings: list[str] = []
    for line in _iter_non_fenced_lines(markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")):
        matched = _match_heading(line)
        if matched is not None:
            headings.append(matched[1])
    return tuple(headings)


def _heading_positions(lines: list[str]) -> list[tuple[int, int, str]]:
    headings: list[tuple[int, int, str]] = []
    in_fence = False
    fence_marker = ""
    for index, line in enumerate(lines):
        fence = _FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if in_fence:
            continue
        matched = _match_heading(line)
        if matched is not None:
            level, heading_text = matched
            headings.append((index, level, heading_text))
    return headings


def normalize_heading_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("#"):
        matched = _ATX_HEADING_RE.match(stripped)
        if matched is not None:
            stripped = _strip_closing_hashes(matched.group(2))
    return _inline_plain(stripped).strip()


def _match_heading(line: str) -> tuple[int, str] | None:
    if line.startswith("    ") or line.startswith("\t"):
        return None
    matched = _ATX_HEADING_RE.match(line)
    if matched is None:
        return None
    level = len(matched.group(1))
    return level, normalize_heading_text(matched.group(2))


def _strip_closing_hashes(text: str) -> str:
    return re.sub(r"\s+#+\s*$", "", text).strip()


def _inline_plain(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("*", "").replace("_", "")
    return text


def _iter_non_fenced_lines(lines: list[str]):
    in_fence = False
    fence_marker = ""
    for line in lines:
        fence = _FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if not in_fence:
            yield line


def _render_code_fence(lines: list[str], start: int, marker: str, language: str) -> tuple[str, int]:
    content: list[str] = []
    index = start + 1
    while index < len(lines):
        close = _FENCE_RE.match(lines[index])
        if close and close.group(1) == marker:
            index += 1
            break
        content.append(lines[index])
        index += 1
    class_attr = f' class="language-{escape(language, quote=True)}"' if language else ""
    return f"<pre><code{class_attr}>{escape(chr(10).join(content))}</code></pre>", index


def _is_horizontal_rule(line: str) -> bool:
    stripped = line.strip()
    return len(stripped) >= 3 and set(stripped) in ({"-"}, {"*"}, {"_"})


def _is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    return "|" in lines[index] and _TABLE_SEPARATOR_RE.match(lines[index + 1]) is not None


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _render_table(lines: list[str], start: int) -> tuple[str, int]:
    headers = _split_table_row(lines[start])
    rows: list[list[str]] = []
    index = start + 2
    while index < len(lines) and "|" in lines[index] and lines[index].strip():
        rows.append(_split_table_row(lines[index]))
        index += 1
    header_html = "".join(f"<th>{_inline_html(cell)}</th>" for cell in headers)
    body_rows = []
    for row in rows:
        body_rows.append("<tr>" + "".join(f"<td>{_inline_html(cell)}</td>" for cell in row) + "</tr>")
    return "<table><thead><tr>" + header_html + "</tr></thead><tbody>" + "".join(body_rows) + "</tbody></table>", index


def _render_list(lines: list[str], start: int) -> tuple[str, int]:
    entries: list[tuple[int, str, str]] = []
    index = start
    while index < len(lines):
        matched = _LIST_ITEM_RE.match(lines[index])
        if matched is None:
            break
        indent = len(matched.group(1).replace("\t", "    "))
        list_type = "ol" if matched.group(2)[0].isdigit() else "ul"
        entries.append((indent // 2, list_type, matched.group(3)))
        index += 1

    html: list[str] = []
    stack: list[str] = []
    current_level = -1
    li_open = False
    for level, list_type, text in entries:
        if level <= current_level and li_open:
            html.append("</li>")
            li_open = False
        while len(stack) > level + 1:
            html.append(f"</{stack.pop()}>")
            current_level -= 1
        if len(stack) == level + 1 and stack[-1] != list_type:
            html.append(f"</{stack.pop()}>")
        while len(stack) < level + 1:
            html.append(f"<{list_type}>")
            stack.append(list_type)
            current_level += 1
        checkbox, item_text = _extract_checkbox(text)
        html.append(f"<li>{checkbox}{_inline_html(item_text)}")
        li_open = True
        current_level = level

    if li_open:
        html.append("</li>")
    while stack:
        html.append(f"</{stack.pop()}>")
    return "".join(html), index


def _extract_checkbox(text: str) -> tuple[str, str]:
    matched = re.match(r"^\[( |x|X)\]\s+(.+)$", text)
    if matched is None:
        return "", text
    checked = " checked" if matched.group(1).lower() == "x" else ""
    return f'<input type="checkbox" disabled{checked}> ', matched.group(2)


def _render_blockquote(lines: list[str], start: int) -> tuple[str, int]:
    quote_lines: list[str] = []
    index = start
    while index < len(lines) and lines[index].lstrip().startswith(">"):
        quote_lines.append(lines[index].lstrip()[1:].lstrip())
        index += 1
    inner = to_html("\n".join(quote_lines))
    return f"<blockquote>{inner}</blockquote>", index


def _render_paragraph(lines: list[str], start: int) -> tuple[str, int]:
    paragraph: list[str] = []
    index = start
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            break
        if paragraph and (
            _FENCE_RE.match(line)
            or _match_heading(line)
            or _is_horizontal_rule(line)
            or _is_table_start(lines, index)
            or _LIST_ITEM_RE.match(line)
            or line.lstrip().startswith(">")
        ):
            break
        paragraph.append(line.strip())
        index += 1
    return f"<p>{_inline_html(' '.join(paragraph))}</p>", index


def _inline_html(text: str) -> str:
    parts: list[str] = []
    index = 0
    while index < len(text):
        if text[index] == "`":
            end = text.find("`", index + 1)
            if end != -1:
                parts.append(f"<code>{escape(text[index + 1:end])}</code>")
                index = end + 1
                continue
        if text.startswith("**", index):
            end = text.find("**", index + 2)
            if end != -1:
                parts.append(f"<strong>{_inline_html(text[index + 2:end])}</strong>")
                index = end + 2
                continue
        if text[index] == "*":
            end = text.find("*", index + 1)
            if end != -1:
                parts.append(f"<em>{_inline_html(text[index + 1:end])}</em>")
                index = end + 1
                continue
        if text[index] == "[":
            matched = re.match(r"\[([^\]]+)\]\(([^)]+)\)", text[index:])
            if matched is not None:
                label, url = matched.group(1), matched.group(2).strip()
                if _is_allowed_url(url):
                    parts.append(
                        f'<a href="{escape(url, quote=True)}">{_inline_html(label)}</a>'
                    )
                else:
                    parts.append(escape(f"{label} ({url})"))
                index += matched.end()
                continue
        parts.append(escape(text[index]))
        index += 1
    return "".join(parts)


def _is_allowed_url(url: str) -> bool:
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        return False
    if any(char in url for char in (" ", "\t", '"', "'", "<", ">")):
        return False
    parsed = urlparse(url)
    if not parsed.scheme:
        return True
    return parsed.scheme.lower() in {"http", "https", "mailto"}
