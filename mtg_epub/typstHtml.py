"""Compila um capítulo .typ para HTML usando o compilador Typst real.
Remove dependências inacessíveis e blocos de configuração corrompidos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import typst
from bs4 import BeautifulSoup

@dataclass
class CompiledChapter:
    title: str | None
    authors: str | None
    body_html: str  # conteúdo interno do <body>

def _matching_close_paren(text: str, opening: int) -> int:
    """Encontra o fechamento seguro de estruturas aninhadas, ignorando strings."""
    depth = 0
    in_string = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if in_string:
            if escaped: escaped = False
            elif char == "\\": escaped = True
            elif char == '"': in_string = False
            continue
        if char == '"': in_string = True
        elif char == "(": depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0: return index
    return -1

def _apply_typst_polyfills(content: str) -> str:
    # 1. Removedor Inteligente de Imports (múltiplas linhas)
    while True:
        match = re.search(r'#import\s+"@local/(?:mtgstory|mtgguide)[^"]+"', content)
        if not match:
            break
        start = match.start()
        cursor = match.end()
        depth = 0
        while cursor < len(content):
            char = content[cursor]
            if char == '(': depth += 1
            elif char == ')': depth -= 1
            elif char == '\n' and depth == 0: break
            cursor += 1
        content = content[:start] + content[cursor:]

    # 2. Remoção Total do bloco #show: conf para blindar contra syntax errors dos .typ originais
    while True:
        match = re.search(r'#show:\s*(?:\w+\s*=>\s*)?conf(?:.*?)\s*\(', content)
        if not match:
            break
        start = match.start()
        opening = content.find("(", start)
        closing = _matching_close_paren(content, opening)
        if closing < 0:
            break
        content = content[:start] + content[closing + 1:]

    # 3. Polyfills blindados contra argumentos nomeados
    polyfill = """
// --- START POLYFILL ---
#let letter_block(..args) = block[#args.pos().join()]
#let epigraph(..args) = block[#args.pos().join()]
#let magic_quote(..args) = block[#args.pos().join()]
// --- END POLYFILL ---
"""
    return polyfill + "\n" + content

def compile_chapter_html(source: Path, root: Path) -> CompiledChapter:
    """Compila um arquivo .typ e manipula a AST do HTML para aplicar regras de estruturação."""
    
    content = source.read_text(encoding="utf-8", errors="replace")
    clean_content = _apply_typst_polyfills(content)
    
    tmp_path = source.with_name(source.name + ".tmp.typ")
    tmp_path.write_text(clean_content, encoding="utf-8")
        
    try:
        raw_html = typst.compile(str(tmp_path), format="html", root=str(root))
    finally:
        tmp_path.unlink(missing_ok=True)

    soup = BeautifulSoup(raw_html, "lxml")
    
    # --- NOVA GARANTIA ESTRUTURAL (POV e Separadores) ---
    for p_tag in soup.find_all("p"):
        children = p_tag.contents
        if len(children) == 1 and children[0].name in ["strong", "b"]:
            h2_tag = soup.new_tag("h2")
            h2_tag.string = children[0].get_text(strip=True)
            p_tag.replace_with(h2_tag)
            
    for polyline in soup.find_all("polyline"):
        if polyline.parent and polyline.parent.name == "svg":
            svg_container = polyline.parent
            if svg_container.parent and svg_container.parent.name == "div":
                hr_tag = soup.new_tag("hr")
                svg_container.parent.replace_with(hr_tag)
    # --- FIM DA GARANTIA ---

    title_tag = soup.find("title")
    authors_tag = soup.find("meta", attrs={"name": "authors"})
    body = soup.find("body")

    if body is None:
        raise ValueError(f"HTML sem <body>: {source}")

    return CompiledChapter(
        title=title_tag.get_text() if title_tag else None,
        authors=authors_tag["content"] if authors_tag else None,
        body_html=body.decode_contents(),
    )