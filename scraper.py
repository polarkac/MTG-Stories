#!/usr/bin/env python3
"""
MTG Stories Scraper & Typst Generator
======================================
Este script extrai histórias e Planeswalker's Guides do site oficial da Wizards of the Coast
(ou espelhos no MTGLore), baixando texto e imagens, e gerando arquivos '.typ' compatíveis
com os pacotes Typst do repositório ('@local/mtgstory' e '@local/mtgguide').

Ele também gerencia o relatório de histórias ausentes, não encontradas ou não-scrappeáveis.
"""

import os
import sys
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
import html as html_lib

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
    'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}

ROOT_DIR = Path("c:/Users/neuro/Documents/mtg-stories/MTG-Stories")
STORIES_DIR = ROOT_DIR / "stories"
GUIDES_DIR = ROOT_DIR / "planeswalkers_guides"
MANIFEST_FILE = ROOT_DIR / "scraped_manifest.json"
MISSING_MD_FILE = ROOT_DIR / "MISSING_STORIES.md"

CATALOG_MISSING = [
    # --- REALITY FRACTURE (SET 064) ---
    {
        "id": "rf-episode-01",
        "type": "story",
        "title": "Reality Fracture | Episode 1: Tam, Alive",
        "clean_title": "Episode 1: Tam, Alive",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "001",
        "author": "Alison Lührs",
        "date": "2026-08-31",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-1-tam-alive",
        "category": "webfiction",
        "notes": "Início do arco Reality Fracture / Echoverse."
    },
    {
        "id": "rf-episode-02",
        "type": "story",
        "title": "Reality Fracture | Episode 2: Purge Yourself of Doubt",
        "clean_title": "Episode 2: Purge Yourself of Doubt",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "002",
        "author": "Alison Lührs",
        "date": "2026-09-01",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-2-purge-yourself-of-doubt",
        "category": "webfiction",
        "notes": "Episódio 2 de Reality Fracture."
    },
    {
        "id": "rf-episode-03",
        "type": "story",
        "title": "Reality Fracture | Episode 3: I Can Be Both",
        "clean_title": "Episode 3: I Can Be Both",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "003",
        "author": "Alison Lührs",
        "date": "2026-09-02",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-3-i-can-be-both",
        "category": "webfiction",
        "notes": "Episódio 3 de Reality Fracture."
    },
    {
        "id": "rf-episode-04",
        "type": "story",
        "title": "Reality Fracture | Episode 4: Oh, Sweetie",
        "clean_title": "Episode 4: Oh, Sweetie",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "004",
        "author": "Alison Lührs",
        "date": "2026-09-03",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-4-oh-sweetie",
        "category": "webfiction",
        "notes": "Episódio 4 de Reality Fracture."
    },
    {
        "id": "rf-episode-05",
        "type": "story",
        "title": "Reality Fracture | Episode 5: I Don't Need to Convince You",
        "clean_title": "Episode 5: I Don't Need to Convince You",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "005",
        "author": "Alison Lührs",
        "date": "2026-09-04",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-5-i-dont-need-to-convince-you",
        "category": "webfiction",
        "notes": "Episódio 5 de Reality Fracture."
    },
    {
        "id": "rf-episode-06",
        "type": "story",
        "title": "Reality Fracture | Episode 6: The Man Who Kills His Own Ambition",
        "clean_title": "Episode 6: The Man Who Kills His Own Ambition",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "006",
        "author": "Alison Lührs",
        "date": "2026-09-05",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-6-the-man-who-kills-his-own-ambition",
        "category": "webfiction",
        "notes": "Episódio 6 de Reality Fracture."
    },
    {
        "id": "rf-episode-07",
        "type": "story",
        "title": "Reality Fracture | Episode 7: Pick Up the Pieces",
        "clean_title": "Episode 7: Pick Up the Pieces",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "007",
        "author": "Alison Lührs",
        "date": "2026-09-08",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-7-pick-up-the-pieces",
        "category": "webfiction",
        "notes": "Episódio 7 de Reality Fracture."
    },
    {
        "id": "rf-episode-08",
        "type": "story",
        "title": "Reality Fracture | Episode 8: Keep Your Lids Open",
        "clean_title": "Episode 8: Keep Your Lids Open",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "008",
        "author": "Alison Lührs",
        "date": "2026-09-09",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-8-keep-your-lids-open",
        "category": "webfiction",
        "notes": "Episódio 8 de Reality Fracture."
    },
    {
        "id": "rf-episode-09",
        "type": "story",
        "title": "Reality Fracture | Episode 9: Unafraid",
        "clean_title": "Episode 9: Unafraid",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "009",
        "author": "Alison Lührs",
        "date": "2026-09-10",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-9-unafraid",
        "category": "webfiction",
        "notes": "Episódio 9 de Reality Fracture."
    },
    {
        "id": "rf-episode-10",
        "type": "story",
        "title": "Reality Fracture | Episode 10: Happy Birthday",
        "clean_title": "Episode 10: Happy Birthday",
        "set_name": "Reality Fracture",
        "set_folder": "064 - Reality Fracture",
        "story_number": "010",
        "author": "Alison Lührs",
        "date": "2026-09-11",
        "url": "https://magic.wizards.com/en/news/magic-story/reality-fracture-episode-10-happy-birthday",
        "category": "webfiction",
        "notes": "Episódio 10 (Final) de Reality Fracture."
    },
    # --- OUTRAS HISTÓRIAS WEB ---
    {
        "id": "duskmourn-its-a-beautiful-day",
        "type": "story",
        "title": "Duskmourn: House of Horror | It's a Beautiful Day",
        "clean_title": "It's a Beautiful Day",
        "set_name": "Duskmourn: House of Horror",
        "set_folder": "058 - Duskmourn: House of Horror",
        "story_number": "012",
        "author": "Mira Grant",
        "date": "2024-08-31",
        "url": "https://magic.wizards.com/en/news/magic-story/side-six-its-a-beautiful-day",
        "mtglore_url": "https://mtglore.com/story/its-a-beautiful-day/",
        "category": "webfiction",
        "notes": "Conto interativo complementar de Duskmourn."
    },
    {
        "id": "tarkir-spirits-of-the-abzan",
        "type": "story",
        "title": "Spirits of the Abzan",
        "clean_title": "Spirits of the Abzan",
        "set_name": "Tarkir: Dragonstorm",
        "set_folder": "060 - Tarkir: Dragonstorm",
        "story_number": "013",
        "author": "Izzy Wasserstein",
        "date": "2026-07-06",
        "url": "https://magic.wizards.com/en/news/magic-story/spirits-of-the-abzan",
        "mtglore_url": "https://mtglore.com/story/spirits-of-the-abzan/",
        "category": "webfiction",
        "notes": "Conto oficial de Tarkir focado em Felothar."
    }
]

UNSCRAPABLE_MEDIA = [
    {
        "title": "Strixhaven: Omens of Chaos",
        "format": "Romance Comercial / Livro (Hardcover, Ebook, Audiobook)",
        "author": "Seanan McGuire",
        "publisher": "Random House Worlds",
        "date": "2026-04-07",
        "reason": "Obra literária comercial protegida por direitos autorais, sem publicação aberta em texto web.",
        "url": "https://mtglore.com/story/strixhaven-omens-of-chaos/"
    },
    {
        "title": "Magic: The Gathering: Untold Stories — Elspeth (#1 a #4)",
        "format": "História em Quadrinhos (Minissérie em 4 edições)",
        "author": "Vários (Dark Horse Comics)",
        "publisher": "Dark Horse Comics",
        "date": "2025-09-17 a 2026-06-03",
        "reason": "Edições impressas/digitais pagas de histórias em quadrinhos canônicas.",
        "url": "https://mtglore.com/story/untold-stories-elspeth-1/"
    },
    {
        "title": "Magic: The Gathering: Untold Stories — Jace (#1 a #4)",
        "format": "História em Quadrinhos (Minissérie em 4 edições)",
        "author": "Vários (Dark Horse Comics)",
        "publisher": "Dark Horse Comics",
        "date": "2026-04-01 a 2026-09-2026",
        "reason": "Edições impressas/digitais pagas de quadrinhos sobre as memórias de Jace.",
        "url": "https://mtglore.com/story/untold-stories-jace-1/"
    },
    {
        "title": "Reality Fracture | The Story So Far with The Magic Story Podcast",
        "format": "Podcast / Áudio Oficial Exclusivo",
        "author": "The Magic Story Podcast / Wizards",
        "publisher": "Wizards of the Coast",
        "date": "2026-07-20",
        "reason": "Episódio narrativo de podcast com recapitulação em áudio, sem texto em prosa.",
        "url": "https://mtglore.com/story/the-story-so-far-with-the-magic-story-podcast/"
    },
    {
        "title": "The Legends of Reality Fracture",
        "format": "Artigo Descritivo de Cards Lendários (Card Lore)",
        "author": "Wizards of the Coast",
        "publisher": "Wizards of the Coast",
        "date": "2026-09-11",
        "reason": "Artigo descritivo de lendas e cartas da coleção, não um conto em prosa.",
        "url": "https://magic.wizards.com/en/news/magic-story/the-legends-of-reality-fracture"
    }
]

def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[\/:*?"<>|]', '-', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -')
    return cleaned

def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as response:
        content_type = response.headers.get('Content-Type', '')
        charset = 'utf-8'
        if 'charset=' in content_type.lower():
            charset = content_type.lower().split('charset=')[-1].split(';')[0].strip()
        data = response.read()
        return data.decode(charset, errors='replace')

def resolve_wizards_url_from_mtglore(mtglore_url: str) -> str:
    try:
        html = fetch_html(mtglore_url)
        matches = re.findall(r'href=[\'"](https://magic\.wizards\.com/[^\'"\s<>]+)[\'"]', html)
        for m in matches:
            if '/news/magic-story/' in m or '/news/feature/' in m:
                return m
    except Exception as e:
        print(f"[Aviso] Falha ao resolver URL Wizards via MTGLore ({mtglore_url}): {e}")
    return mtglore_url

def parse_date_string(date_str: str) -> tuple[int, int, int]:
    date_str = date_str.strip()
    iso_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})', date_str)
    if iso_match:
        return int(iso_match.group(3)), int(iso_match.group(2)), int(iso_match.group(1))
    
    for fmt in ('%b %d, %Y', '%B %d, %Y', '%b %d %Y', '%B %d %Y'):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.day, dt.month, dt.year
        except ValueError:
            pass
    return 1, 1, 2026

def convert_html_snippet_to_typst(snippet: str) -> str:
    text = snippet
    text = html_lib.unescape(text)
    text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace('$', r'\$')
    
    def replace_link(m):
        href = m.group(1).strip()
        link_text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if not link_text:
            return ""
        return f'#link("{href}")[{link_text}]'
    text = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', replace_link, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'*\2*', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'_ \2 _', text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace('_ *', '_*').replace('* _', '*_')
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text

def parse_article_html(html: str, default_metadata: dict = None) -> dict:
    meta = default_metadata.copy() if default_metadata else {}
    
    title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    if not title_match:
        title_match = re.search(r'<h1[^>]*><span>(.*?)</span></h1>', html)
    if not title_match:
        title_match = re.search(r'<title>(.*?)</title>', html)
    if title_match and not meta.get("clean_title"):
        raw_title = html_lib.unescape(title_match.group(1)).strip()
        cleaned = re.sub(r'^.*\|\s*', '', raw_title)
        meta["clean_title"] = cleaned
    
    date_match = re.search(r'<time[^>]*>(.*?)</time>', html)
    if date_match and not meta.get("date"):
        meta["date"] = date_match.group(1).strip()
    
    author_match = re.search(r'class="css-IqqMm">\s*([^<]+)\s*<', html)
    if not author_match:
        author_match = re.search(r'author=["\'][^"\']*["\'][^>]*>\s*<[^>]+>\s*([^<]+)<', html)
    if not author_match:
        author_match = re.search(r'By\s+<[^>]+>([^<]+)<', html, re.IGNORECASE)
    if author_match and not meta.get("author"):
        meta["author"] = author_match.group(1).strip()
    
    og_img_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)
    if not og_img_match:
        og_img_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    hero_image_url = og_img_match.group(1).strip() if og_img_match else None
    
    body_html = ""
    art_start = html.find('class="article-body')
    if art_start != -1:
        art_end = html.find('</article>', art_start)
        body_html = html[art_start:art_end] if art_end != -1 else html[art_start:art_start+150000]
    elif '<article' in html:
        art_start = html.find('<article')
        art_end = html.find('</article>', art_start)
        body_html = html[art_start:art_end]
    else:
        body_html = html
    
    elements = []
    block_regex = re.compile(r'(<p[^>]*>.*?</p>|<hr[^>]*>|<h[23][^>]*>.*?</h[23]>|<figure[^>]*>.*?</figure>|<img[^>]+>)', re.DOTALL | re.IGNORECASE)
    matches = block_regex.findall(body_html)
    
    for tag in matches:
        lower = tag.lower()
        if lower.startswith('<p'):
            inner = re.sub(r'^<p[^>]*>|</p>$', '', tag, flags=re.IGNORECASE)
            img_in_p = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', inner)
            if img_in_p:
                caption_match = re.search(r'(Art by:?[^<]+|Illustrated by[^<]+)', inner, re.IGNORECASE)
                elements.append({
                    "type": "image",
                    "src": img_in_p.group(1),
                    "caption": caption_match.group(1).strip() if caption_match else ""
                })
            else:
                p_text = convert_html_snippet_to_typst(inner)
                if p_text:
                    if p_text.lower().startswith("art by") or p_text.lower().startswith("illustration by"):
                        if elements and elements[-1]["type"] == "image" and not elements[-1]["caption"]:
                            elements[-1]["caption"] = p_text
                            continue
                    elements.append({"type": "paragraph", "text": p_text})
        elif lower.startswith('<hr'):
            elements.append({"type": "divider"})
        elif lower.startswith('<h2'):
            inner = re.sub(r'^<h2[^>]*>|</h2>$', '', tag, flags=re.IGNORECASE)
            elements.append({"type": "heading_1", "text": convert_html_snippet_to_typst(inner)})
        elif lower.startswith('<h3'):
            inner = re.sub(r'^<h3[^>]*>|</h3>$', '', tag, flags=re.IGNORECASE)
            elements.append({"type": "heading_2", "text": convert_html_snippet_to_typst(inner)})
        elif lower.startswith('<figure') or lower.startswith('<img'):
            img_src = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', tag)
            caption_match = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', tag, re.DOTALL | re.IGNORECASE)
            if img_src:
                elements.append({
                    "type": "image",
                    "src": img_src.group(1),
                    "caption": convert_html_snippet_to_typst(caption_match.group(1)) if caption_match else ""
                })
    
    return {
        "metadata": meta,
        "hero_image": hero_image_url,
        "elements": elements
    }

def download_image(url: str, dest_path: Path) -> bool:
    try:
        if url.startswith("//"):
            url = "https:" + url
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            with open(dest_path, "wb") as f:
                f.write(data)
        return True
    except Exception as e:
        print(f"[Aviso] Falha ao baixar imagem ({url}): {e}")
        return False

def generate_story_typst(parsed: dict, output_typ_path: Path, image_dir_rel: str) -> None:
    meta = parsed["metadata"]
    title = meta.get("clean_title", "Untitled Story")
    set_name = meta.get("set_name", "Unknown Set")
    author = meta.get("author", "Unknown Author")
    day, month, year = parse_date_string(meta.get("date", "2026-09-01"))
    
    typ_lines = [
        '#import "@local/mtgstory:0.2.0": conf',
        '#show: doc => conf(',
        f'    "{title}",',
        f'    set_name: "{set_name}",',
        f'    story_date: datetime(day: {day:02d}, month: {month:02d}, year: {year}),',
        f'    author: "{author}",',
        '    doc',
        ')',
        ''
    ]
    
    img_counter = 1
    image_folder_abs = output_typ_path.parent / image_dir_rel
    
    has_inline_images = any(el["type"] == "image" for el in parsed["elements"])
    if not has_inline_images and parsed.get("hero_image"):
        img_name = f"{img_counter:02d}.jpg"
        if download_image(parsed["hero_image"], image_folder_abs / img_name):
            rel_img = f"{image_dir_rel}/{img_name}"
            typ_lines.append(f'#figure(image("{rel_img}", width: 100%), caption: [Art from {set_name}], supplement: none, numbering: none)\n')
            img_counter += 1

    for el in parsed["elements"]:
        el_type = el["type"]
        if el_type == "paragraph":
            typ_lines.append(el["text"] + "\n")
        elif el_type == "divider":
            typ_lines.extend([
                '#v(0.35em)',
                '#line(length: 100%, stroke: rgb(90%, 90%, 90%))',
                '#v(0.35em)\n'
            ])
        elif el_type == "heading_1":
            typ_lines.append(f'= {el["text"]}\n')
        elif el_type == "heading_2":
            typ_lines.append(f'== {el["text"]}\n')
        elif el_type == "image":
            img_name = f"{img_counter:02d}.jpg"
            if download_image(el["src"], image_folder_abs / img_name):
                rel_img = f"{image_dir_rel}/{img_name}"
                cap = el.get("caption", "").strip()
                cap_code = f'caption: [{cap}]' if cap else 'caption: none'
                typ_lines.append(f'#figure(image("{rel_img}", width: 100%), {cap_code}, supplement: none, numbering: none)\n')
                img_counter += 1

    output_typ_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_typ_path, "w", encoding="utf-8") as f:
        f.write("\n".join(typ_lines))
    print(f"[OK] História gerada com sucesso: {output_typ_path}")

def generate_set_file_if_needed(set_name: str, set_folder_name: str, stories_list: list[str]) -> None:
    """Gera o arquivo de conjunto correspondente (ex: stories/064_Reality Fracture.typ)."""
    prefix = set_folder_name.split(" - ")[0]
    set_clean = set_folder_name.split(" - ")[-1]
    set_file_path = STORIES_DIR / f"{prefix}_{set_clean}.typ"
    
    lines = [
        '#import "@local/mtgset:0.1.0": conf',
        f'#show: doc => conf("{set_name}", doc)',
        ''
    ]
    for s in sorted(stories_list):
        lines.append(f'#include "./{set_folder_name}/{s}"')
    
    with open(set_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[OK] Arquivo do Set gerado: {set_file_path}")

def scrape_single_item(item: dict) -> dict:
    item_id = item.get("id", sanitize_filename(item.get("title", "custom")))
    print(f"\n--- Processando: {item.get('title', item_id)} ---")
    
    url = item.get("url")
    html_content = None
    fetched_from = url
    try:
        print(f"Buscando URL oficial: {url}")
        html_content = fetch_html(url)
    except Exception as e:
        print(f"[Aviso] Falha ao obter URL primária ({url}): {e}")
        if item.get("mtglore_url"):
            print(f"Tentando resolver link da Wizards via MTGLore: {item['mtglore_url']}")
            resolved_url = resolve_wizards_url_from_mtglore(item["mtglore_url"])
            if resolved_url and resolved_url != url:
                try:
                    html_content = fetch_html(resolved_url)
                    fetched_from = resolved_url
                except Exception as e2:
                    print(f"[Erro] Falha ao obter URL resolvida ({resolved_url}): {e2}")

    if not html_content:
        return {
            "id": item_id,
            "title": item.get("title"),
            "status": "failed",
            "error": "Não foi possível baixar o HTML da página oficial."
        }

    parsed = parse_article_html(html_content, default_metadata=item)
    
    item_type = item.get("type", "story")
    if item_type == "story":
        set_folder = sanitize_filename(item.get("set_folder", f"Unknown - {item.get('set_name', 'Unknown')}"))
        story_num = item.get("story_number", "001")
        clean_title = sanitize_filename(parsed["metadata"].get("clean_title", "Story"))
        file_basename = f"{story_num}_{clean_title}"
        target_typ = STORIES_DIR / set_folder / f"{file_basename}.typ"
        image_dir_rel = file_basename
        generate_story_typst(parsed, target_typ, image_dir_rel)
    else:
        guide_folder = sanitize_filename(item.get("guide_folder", f"{item.get('guide_number', '005')} - {item.get('title', 'Guide')}"))
        guide_file_name = sanitize_filename(f"{item.get('guide_number', '005')} - {item.get('clean_title', 'Guide')}.typ")
        target_typ = GUIDES_DIR / guide_folder / guide_file_name
        image_dir_rel = "images"
        generate_story_typst(parsed, target_typ, image_dir_rel)

    return {
        "id": item_id,
        "title": parsed["metadata"].get("clean_title"),
        "author": parsed["metadata"].get("author"),
        "date": parsed["metadata"].get("date"),
        "status": "scraped",
        "output_file": str(target_typ.relative_to(ROOT_DIR)),
        "file_name": target_typ.name,
        "set_folder": set_folder if item_type == "story" else None,
        "set_name": item.get("set_name"),
        "source_url": fetched_from
    }

def update_manifest_and_docs(results: list[dict]) -> None:
    manifest = {
        "last_run": datetime.now().isoformat(),
        "scraped_items": {},
        "unscrapable_media": UNSCRAPABLE_MEDIA
    }
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                old = json.load(f)
                manifest["scraped_items"] = old.get("scraped_items", {})
        except Exception:
            pass

    for r in results:
        manifest["scraped_items"][r["id"]] = r

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifesto de scraping atualizado: {MANIFEST_FILE}")

    generate_missing_md_file(manifest)

def generate_missing_md_file(manifest: dict) -> None:
    scraped_map = manifest.get("scraped_items", {})
    
    md = [
        "# Catálogo de Histórias Faltantes e Mídias Não-Scrappeáveis",
        "",
        "Este documento rastreia a cobertura de histórias de **Magic: The Gathering** no repositório, "
        "identificando o que já foi extraído pelo scraper, o que permanece pendente e quais obras **não podem ser scrappeadas** "
        "por pertencerem a mídias pagas, licenciadas ou audiovisuais (como rastreadas pelo [MTGLore](https://mtglore.com/chronological/)).",
        "",
        "---",
        "",
        "## 1. Status de Webfiction Oficial (Contos Faltantes)",
        "",
        "| ID | Coleção | Título / Episódio | Autor | Data | Status no Repositório |",
        "| :--- | :--- | :--- | :--- | :---: | :---: |"
    ]

    stories = [item for item in CATALOG_MISSING if item.get("type") == "story"]
    for s in stories:
        sid = s["id"]
        res = scraped_map.get(sid)
        status_tag = "✅ Scrappeado" if (res and res.get("status") == "scraped") else "⏳ Pendente"
        md.append(f"| `{sid}` | {s['set_name']} | **{s['clean_title']}** | {s['author']} | {s['date']} | {status_tag} |")

    md.extend([
        "",
        "---",
        "",
        "## 2. Histórias e Mídias NÃO-SCRAPPEÁVEIS (Fora do Escopo Web / Pagas / Áudio)",
        "",
        "Estas obras constam na linha do tempo cronológica do MTGLore, porém **não podem ser extraídas diretamente por web scraping** "
        "nem devem ser adicionadas como texto aberto, pelos motivos descritos abaixo:",
        "",
        "| Título / Série | Formato Original | Editora / Fonte | Data | Motivo de Incompatibilidade com o Scraper |",
        "| :--- | :--- | :--- | :---: | :--- |"
    ])

    for u in UNSCRAPABLE_MEDIA:
        md.append(f"| **{u['title']}** | {u['format']} | {u['publisher']} | {u['date']} | {u['reason']} |")

    md.extend([
        "",
        "---",
        "",
        "## 3. Como Executar o Scraper",
        "",
        "```bash",
        "# Scrappear todas as histórias do catálogo:",
        "python scraper.py --all",
        "",
        "# Scrappear apenas Reality Fracture:",
        "python scraper.py --rf",
        "```",
        ""
    ])

    with open(MISSING_MD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"[OK] Documento de acompanhamento atualizado: {MISSING_MD_FILE}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MTG Stories Scraper & Typst Generator")
    parser.add_argument("--all", action="store_true", help="Scrappeia todas as histórias pendentes do catálogo")
    parser.add_argument("--rf", action="store_true", help="Scrappeia apenas os 10 episódios de Reality Fracture")
    parser.add_argument("--id", type=str, help="Scrappeia um item específico pelo ID do catálogo")
    parser.add_argument("--status", action="store_true", help="Apenas atualiza o relatório e MISSING_STORIES.md")

    args = parser.parse_args()

    if args.status:
        update_manifest_and_docs([])
        return

    targets = []
    if args.rf:
        targets = [it for it in CATALOG_MISSING if it["id"].startswith("rf-")]
    elif args.id:
        found = [it for it in CATALOG_MISSING if it["id"] == args.id]
        if not found:
            print(f"[Erro] ID '{args.id}' não encontrado no catálogo.")
            sys.exit(1)
        targets = found
    else:
        # Por padrão ou com --all, executa os de Reality Fracture
        targets = [it for it in CATALOG_MISSING if it["id"].startswith("rf-")]

    results = []
    rf_files = []
    for item in targets:
        res = scrape_single_item(item)
        results.append(res)
        if res.get("status") == "scraped" and res.get("set_name") == "Reality Fracture":
            rf_files.append(res["file_name"])

    # Se Reality Fracture foi scrappeado, gera o arquivo do set 064_Reality Fracture.typ
    if rf_files:
        generate_set_file_if_needed("Reality Fracture", "064 - Reality Fracture", rf_files)
        
        # Atualiza COMPLETE_STORIES.typ se ainda não incluir o set 064
        cs_path = ROOT_DIR / "COMPLETE_STORIES.typ"
        if cs_path.exists():
            with open(cs_path, "r", encoding="utf-8") as f:
                cs_content = f.read()
            if "064_Reality Fracture.typ" not in cs_content:
                cs_content += '\n#include "./stories/064_Reality Fracture.typ"\n'
                with open(cs_path, "w", encoding="utf-8") as f:
                    f.write(cs_content)
                print("[OK] COMPLETE_STORIES.typ atualizado com Reality Fracture!")

    update_manifest_and_docs(results)
    print("\nProcessamento concluído!")

if __name__ == "__main__":
    main()
