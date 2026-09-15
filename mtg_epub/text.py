from __future__ import annotations

from pathlib import Path


def _matching_close_paren(text: str, opening: int) -> int:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == '"':
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def remove_conf_block(content: str) -> str:
    """Remove imports and the balanced MTGStory conf application."""
    import_marker = content.find("#import")
    show_marker = content.find("#show:")
    if import_marker >= 0 and show_marker >= 0 and import_marker < show_marker:
        content = content[:import_marker] + content[show_marker:]

    marker = "#show: doc => conf"
    start = content.find(marker)
    if start < 0:
        return content
    opening = content.find("(", start + len(marker))
    if opening < 0:
        return content
    closing = _matching_close_paren(content, opening)
    if closing < 0:
        raise ValueError("Unclosed Typst conf block")
    return content[:start] + content[closing + 1 :]


def sanitize_typst_for_pandoc(content: str, base_dir: Path) -> str:
    clean = remove_conf_block(content)
    clean = _replace_balanced_call(clean, "#line", "---")
    clean = _remove_balanced_call(clean, "#v")
    clean = _replace_bracket_call(clean, "#emph", "", "")
    clean = _replace_bracket_call(clean, "#strong", "", "")

    import re

    def replace_image(match: re.Match[str]) -> str:
        relative = match.group(1)
        absolute = (base_dir / relative).resolve()
        return f'image("{absolute.as_posix()}"'

    return re.sub(r'image\s*\(\s*["\']([^"\']+)["\']', replace_image, clean)


def _replace_balanced_call(content: str, name: str, replacement: str) -> str:
    result: list[str] = []
    cursor = 0
    while True:
        start = content.find(name + "(", cursor)
        if start < 0:
            result.append(content[cursor:])
            return "".join(result)
        result.append(content[cursor:start])
        opening = start + len(name)
        closing = _matching_close_paren(content, opening)
        if closing < 0:
            raise ValueError(f"Unclosed Typst call: {name}")
        result.append(replacement)
        cursor = closing + 1


def _remove_balanced_call(content: str, name: str) -> str:
    return _replace_balanced_call(content, name, "")


def _matching_close_bracket(text: str, opening: int) -> int:
    depth = 0
    for index in range(opening, len(text)):
        char = text[index]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _replace_bracket_call(content: str, name: str, prefix: str, suffix: str) -> str:
    result: list[str] = []
    cursor = 0
    while True:
        start = content.find(name + "[", cursor)
        if start < 0:
            result.append(content[cursor:])
            return "".join(result)
        result.append(content[cursor:start])
        opening = start + len(name)
        closing = _matching_close_bracket(content, opening)
        if closing < 0:
            raise ValueError(f"Unclosed Typst call: {name}")
        result.extend((prefix, content[opening + 1:closing], suffix))
        cursor = closing + 1
