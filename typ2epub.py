#!/usr/bin/env python3
"""
Typst to EPUB Converter for MTG Stories
========================================
Converte arquivos de histórias Typst (.typ) em livros digitais EPUB padronizados e elegantes.

Principais Recursos:
- Extração de metadados de Autor (com fallback direto na leitura do início do arquivo).
- Metadados de Série (Coleção/Set) e indexação/ordenação numérica (Episode / Story Number).
- Suporte duplo a metadados de série: Calibre (calibre:series / calibre:series_index) e EPUB 3 (belongs-to-collection).
- Capa automática extraída da primeira imagem na pasta designada da história.
- Tipografia e formatação limpas (XHTML + CSS otimizado para e-readers: Kindle, Kobo, Apple Books, Calibre).
- Conversão individual (--file), por coleção (--set) ou em lote (--all).
- Opção para gerar volume unificado da coleção inteira (--combine).
"""

import os
import sys
import re
import zipfile
import uuid
import mimetypes
import argparse
from pathlib import Path
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

ROOT_DIR = Path(__file__).resolve().parent
STORIES_DIR = ROOT_DIR / "stories"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "epubs"

EPUB_CSS = """
@charset "utf-8";
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.6;
    margin: 5% 6%;
    color: #1a1a1a;
    background-color: #fafafa;
    text-align: justify;
    -webkit-hyphens: auto;
    hyphens: auto;
}

h1.story-title {
    font-size: 1.8em;
    line-height: 1.25;
    margin-top: 1.5em;
    margin-bottom: 0.2em;
    text-align: center;
    font-weight: bold;
    color: #111;
}

.story-meta {
    text-align: center;
    font-style: italic;
    font-size: 0.95em;
    color: #555;
    margin-bottom: 2em;
    border-bottom: 1px solid #ddd;
    padding-bottom: 1em;
}

.story-meta .author {
    font-weight: bold;
    color: #222;
}

.story-meta .set-name {
    display: block;
    margin-top: 0.3em;
    font-size: 0.9em;
    color: #666;
}

h2 {
    font-size: 1.35em;
    margin-top: 1.8em;
    margin-bottom: 0.5em;
    color: #222;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.2em;
}

h3 {
    font-size: 1.15em;
    margin-top: 1.4em;
    margin-bottom: 0.4em;
    color: #333;
}

p {
    margin-top: 0;
    margin-bottom: 0.85em;
    text-indent: 1.2em;
}

p.first-p, h1 + p, h2 + p, h3 + p, hr + p, figure + p, blockquote + p {
    text-indent: 0;
}

blockquote {
    margin: 1.2em 1.5em;
    padding: 0.6em 1em;
    border-left: 3px solid #777;
    background-color: #f2f2f2;
    font-style: italic;
}

blockquote p {
    text-indent: 0;
    margin-bottom: 0.5em;
}

hr.scene-break {
    border: none;
    text-align: center;
    margin: 2em 0;
    height: 1.5em;
}

hr.scene-break:before {
    content: "*  *  *";
    color: #777;
    font-size: 1.1em;
    letter-spacing: 0.3em;
}

figure.story-image {
    margin: 1.8em 0;
    text-align: center;
}

figure.story-image img {
    max-width: 100%;
    height: auto;
    border-radius: 3px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.15);
}

figcaption {
    font-size: 0.85em;
    color: #666;
    margin-top: 0.5em;
    font-style: italic;
    text-align: center;
}

.cover-container {
    text-align: center;
    margin: 0;
    padding: 0;
    height: 100vh;
}

.cover-container img {
    max-width: 100%;
    max-height: 100%;
    height: auto;
    width: auto;
    object-fit: contain;
}
"""

def extract_metadata_from_typ(file_path: Path) -> dict:
    """Extrai metadados do arquivo .typ com fallbacks para autor, título e set."""
    content = file_path.read_text(encoding="utf-8", errors="replace")
    
    # 1. Título — conf() usa aspas duplas; NÃO usar [^"'] pois corta títulos com apóstrofo (ex: "I Don't...")
    title_match = re.search(r'#show:\s*doc\s*=>\s*conf\s*\(\s*"([^"]+)"', content)
    if not title_match:
        title_match = re.search(r'conf\s*\(\s*"([^"]+)"', content)
    
    # 2. Set Name (Coleção)
    set_match = re.search(r'set_name:\s*["\']([^"\']+)["\']', content)
    
    # 3. Autor
    author_match = re.search(r'author:\s*["\']([^"\']+)["\']', content)
    
    # 4. Data
    date_match = re.search(r'story_date:\s*datetime\s*\(\s*day:\s*(\d+),\s*month:\s*(\d+),\s*year:\s*(\d+)\s*\)', content)
    if not date_match:
        date_match = re.search(r'date:\s*datetime\s*\(\s*day:\s*(\d+),\s*month:\s*(\d+),\s*year:\s*(\d+)\s*\)', content)
        
    # --- FALLBACKS ---
    # Fallback para Título: remove numeração inicial do nome do arquivo (ex: '001_Episode 1' -> 'Episode 1')
    if title_match and title_match.group(1).strip() and title_match.group(1).strip() != "Untitled":
        title = title_match.group(1).strip()
    else:
        clean_name = re.sub(r'^\d+[\s_-]*', '', file_path.stem)
        title = clean_name.replace('-', ': ') if '-' in clean_name else clean_name
        
    # Fallback para Set: busca no nome da pasta pai (ex: '064 - Reality Fracture' -> 'Reality Fracture')
    if set_match and set_match.group(1).strip() and set_match.group(1).strip() != "Unknown set":
        set_name = set_match.group(1).strip()
    else:
        parent_name = file_path.parent.name
        set_name = re.sub(r'^\d+[\s_-]*', '', parent_name).strip(' -')
        if not set_name:
            set_name = "Magic: The Gathering Stories"

    # Fallback para Autor: analisa as primeiras 30 linhas procurando menções como "by Author"
    author = "Unknown Author"
    if author_match and author_match.group(1).strip() and author_match.group(1).strip() != "Unknown author":
        author = author_match.group(1).strip()
    else:
        first_lines = content.splitlines()[:35]
        for line in first_lines:
            by_m = re.search(r'\b(?:by|por)\s+([A-ZÀ-ÿ][A-Za-zÀ-ÿ\s\.\-]{2,40})', line, re.IGNORECASE)
            if by_m and "magic" not in by_m.group(1).lower() and "wizard" not in by_m.group(1).lower():
                author = by_m.group(1).strip()
                break
        if author == "Unknown Author":
            author = "Wizards of the Coast"

    # Fallback para Data
    if date_match:
        day, month, year = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
        story_date = f"{year:04d}-{month:02d}-{day:02d}"
    else:
        story_date = ""  # vazio se não encontrar data de publicação

    # Número / Índice na série (ordenado pelo n° do livro na série)
    num_match = re.match(r'^(\d+)', file_path.stem)
    series_index = int(num_match.group(1)) if num_match else 1

    # 5. Número do Set (NNN) — extraído do nome da pasta pai (ex: '064 - Reality Fracture' -> '064')
    set_num_match = re.match(r'^(\d+)\s*-', file_path.parent.name)
    set_number = set_num_match.group(1) if set_num_match else ""

    # 6. URL de origem — busca link da Wizards que corresponda ao nome do arquivo atual
    #    Os .typ têm uma barra de navegação com links para outros episódios, então tentamos
    #    encontrar o link que mais se parece com o slug deste arquivo especificamente.
    all_wotc_links = re.findall(r'#link\("(https://magic\.wizards\.com/[^"]+)"', content)
    source_url = ""
    if all_wotc_links:
        # Tenta encontrar o link que contém o slug do arquivo (sem numeração)
        stem_slug = re.sub(r'^\d+[_\s-]*', '', file_path.stem).lower()
        stem_slug = re.sub(r'[^a-z0-9]+', '-', stem_slug).strip('-')
        for link in all_wotc_links:
            link_slug = link.rstrip('/').split('/')[-1].lower()
            if stem_slug[:12] in link_slug or link_slug[:12] in stem_slug:
                source_url = link
                break
        # Fallback: usa o primeiro link encontrado
        if not source_url:
            source_url = all_wotc_links[0]

    # 7. Artistas (ilustradores) — extraídos de caption: [Art by X] ou [Art by: X]
    artist_raw = re.findall(r'caption:\s*\[([^\]]+)\]', content)
    artists = set()
    for cap in artist_raw:
        # Suporta "Art by Foo", "Art by: Foo", "Illustrated by Foo", etc.
        art_match = re.search(
            r'(?:Art by|Illustrated by|Illus\. by)\s*:?\s*([^|\]<\n,]+)',
            cap, re.IGNORECASE
        )
        if art_match:
            name = art_match.group(1).strip().rstrip('.,')
            if name and len(name) > 2:
                artists.add(name)


    return {
        "title": title,
        "set_name": set_name,
        "author": author,
        "date": story_date,
        "series": set_name,
        "series_index": series_index,
        "set_number": set_number,
        "source_url": source_url,
        "artists": sorted(artists),
        "file_path": file_path
    }


def find_cover_image(typ_path: Path) -> Path | None:
    """Encontra a primeira imagem na pasta designada da história."""
    # 1. Pasta designada com mesmo nome base do arquivo .typ
    story_folder = typ_path.parent / typ_path.stem
    if story_folder.exists() and story_folder.is_dir():
        imgs = sorted(list(story_folder.glob("*.jpg")) + list(story_folder.glob("*.jpeg")) + list(story_folder.glob("*.png")) + list(story_folder.glob("*.webp")))
        if imgs:
            return imgs[0]
            
    # 2. Pasta com dois-pontos adaptados ou variações
    for sub in typ_path.parent.iterdir():
        if sub.is_dir() and (sub.name.startswith(typ_path.stem[:4]) or sub.name == typ_path.stem):
            imgs = sorted(list(sub.glob("*.jpg")) + list(sub.glob("*.png")))
            if imgs:
                return imgs[0]

    # 3. Subpasta images/
    img_dir = typ_path.parent / "images"
    if img_dir.exists():
        imgs = sorted(list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")))
        if imgs:
            return imgs[0]

    return None

def typst_to_xhtml_body(content: str, typ_path: Path, image_map: dict) -> tuple[str, list[Path]]:
    """Converte o corpo do arquivo Typst em XHTML estruturado e rastreia imagens."""
    # Remove bloco inicial de configuração conf(...)
    body_text = re.sub(r'#import\s+["\'][^"\']+["\'].*?(?=#show|\Z)', '', content, flags=re.DOTALL)
    body_text = re.sub(r'#show:\s*doc\s*=>\s*conf\s*\(.*?\)\s*', '', body_text, flags=re.DOTALL)

    lines = body_text.splitlines()
    xhtml_parts = []
    referenced_images = []
    
    in_letter_block = False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        
        if not line:
            continue

        # Início/Fim de letter_block ou quote
        if "#letter_block" in line or "#quote" in line:
            in_letter_block = True
            xhtml_parts.append("<blockquote>")
            line = re.sub(r'#(?:letter_block|quote)[^\[]*\[', '', line)
            if not line.strip():
                continue
                
        if in_letter_block and line.endswith("]"):
            in_letter_block = False
            line = line[:-1]
            close_quote = True
        else:
            close_quote = False

        # Divisor de cena
        if line.startswith("#line(") or line.startswith("#v(") or line == "---":
            # Pula linha subsequente se for outro elemento do separador
            if i < len(lines) and (lines[i].strip().startswith("#line(") or lines[i].strip().startswith("#v(")):
                i += 1
            xhtml_parts.append('<hr class="scene-break" />')
            continue

        # Figura / Imagem
        if line.startswith("#figure("):
            img_m = re.search(r'image\s*\(\s*["\']([^"\']+)["\']', line)
            cap_m = re.search(r'caption:\s*\[(.*?)\]', line)
            
            if img_m:
                raw_rel_img = img_m.group(1).replace("\\", "/")
                # Resolver imagem no disco
                img_disk_path = (typ_path.parent / raw_rel_img).resolve()
                if not img_disk_path.exists():
                    # Tentar caminhos alternativos
                    cand = typ_path.parent / Path(raw_rel_img).name
                    if cand.exists():
                        img_disk_path = cand
                        
                caption_text = cap_m.group(1).strip() if cap_m else ""
                if img_disk_path.exists():
                    img_id = f"img_{len(referenced_images)+1:02d}{img_disk_path.suffix.lower()}"
                    referenced_images.append(img_disk_path)
                    image_map[img_disk_path] = img_id
                    
                    cap_html = f"<figcaption>{xml_escape(caption_text)}</figcaption>" if caption_text else ""
                    xhtml_parts.append(f'<figure class="story-image"><img src="images/{img_id}" alt="Illustration" />{cap_html}</figure>')
            continue

        # Títulos
        if line.startswith("="):
            level = len(re.match(r'^=+', line).group(0))
            clean_head = line.lstrip("= ").strip()
            tag = f"h{min(level + 1, 4)}"
            xhtml_parts.append(f"<{tag}>{xml_escape(clean_head)}</{tag}>")
            continue

        # Formatação inline para parágrafos
        text = xml_escape(line)
        # Bold
        text = re.sub(r'\*([^\*]+)\*', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
        text = re.sub(r'#emph\[(.*?)\]', r'<em>\1</em>', text)
        # Links
        text = re.sub(r'#link\("([^"]+)"\)\[(.*?)\]', r'<a href="\1">\2</a>', text)

        xhtml_parts.append(f"<p>{text}</p>")
        
        if close_quote:
            xhtml_parts.append("</blockquote>")

    if in_letter_block:
        xhtml_parts.append("</blockquote>")

    return "\n".join(xhtml_parts), referenced_images

def build_epub_for_story(typ_path: Path, output_epub_path: Path) -> bool:
    """Gera um arquivo EPUB completo e padronizado a partir de um arquivo .typ."""
    meta = extract_metadata_from_typ(typ_path)
    content = typ_path.read_text(encoding="utf-8", errors="replace")
    
    image_map = {}
    cover_image_path = find_cover_image(typ_path)
    
    body_xhtml, ref_images = typst_to_xhtml_body(content, typ_path, image_map)
    
    # Se encontrou capa, garantir que ela esteja na lista de imagens
    if cover_image_path and cover_image_path not in image_map:
        cover_id = f"cover{cover_image_path.suffix.lower()}"
        image_map[cover_image_path] = cover_id
    elif cover_image_path:
        cover_id = image_map[cover_image_path]
    else:
        cover_id = None

    book_uuid = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_DNS, str(typ_path))}"
    
    output_epub_path.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(output_epub_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. mimetype (precisa ser descompactado e o primeiro arquivo no zip)
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        
        # 2. META-INF/container.xml
        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
        zf.writestr("META-INF/container.xml", container_xml)
        
        # 3. CSS
        zf.writestr("OEBPS/styles.css", EPUB_CSS)
        
        # 4. Imagens
        manifest_items = [
            '<item id="css" href="styles.css" media-type="text/css"/>',
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        ]
        
        if cover_id and cover_image_path:
            cover_mime = mimetypes.guess_type(cover_image_path.name)[0] or "image/jpeg"
            zf.write(cover_image_path, f"OEBPS/images/{cover_id}")
            manifest_items.append(f'<item id="cover-image" href="images/{cover_id}" media-type="{cover_mime}" properties="cover-image"/>')
            manifest_items.append('<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>')
            
            # Página de capa
            cover_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>Cover</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body style="margin:0; padding:0;">
    <div class="cover-container">
        <img src="images/{cover_id}" alt="Cover Image"/>
    </div>
</body>
</html>"""
            zf.writestr("OEBPS/cover.xhtml", cover_xhtml)

        for img_path, img_name in image_map.items():
            if img_name != cover_id and img_path.exists():
                mime = mimetypes.guess_type(img_path.name)[0] or "image/jpeg"
                zf.write(img_path, f"OEBPS/images/{img_name}")
                manifest_items.append(f'<item id="{img_name.replace(".", "_")}" href="images/{img_name}" media-type="{mime}"/>')

        # 5. Capítulo Principal (XHTML)
        chapter_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>{xml_escape(meta['title'])}</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <h1 class="story-title">{xml_escape(meta['title'])}</h1>
    <div class="story-meta">
        <span class="author">by {xml_escape(meta['author'])}</span>
        <span class="set-name">{xml_escape(meta['set_name'])} • {xml_escape(meta['date'])}</span>
    </div>
    <div class="story-content">
{body_xhtml}
    </div>
</body>
</html>"""
        zf.writestr("OEBPS/chapter.xhtml", chapter_xhtml)

        # 6. Nav XHTML (EPUB 3)
        nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>Table of Contents</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
            <li><a href="chapter.xhtml">{xml_escape(meta['title'])}</a></li>
        </ol>
    </nav>
</body>
</html>"""
        zf.writestr("OEBPS/nav.xhtml", nav_xhtml)

        # 7. NCX (EPUB 2 / Compatibilidade)
        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="{book_uuid}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{xml_escape(meta['title'])}</text></docTitle>
    <docAuthor><text>{xml_escape(meta['author'])}</text></docAuthor>
    <navMap>
        <navPoint id="navpoint-1" playOrder="1">
            <navLabel><text>{xml_escape(meta['title'])}</text></navLabel>
            <content src="chapter.xhtml"/>
        </navPoint>
    </navMap>
</ncx>"""
        zf.writestr("OEBPS/toc.ncx", toc_ncx)

        # 8. Content.opf (Metadados Calibre + EPUB 3 Series + Spine)
        spine_items = []
        if cover_id:
            spine_items.append('<itemref idref="cover-page"/>')
        spine_items.append('<itemref idref="chapter"/>')

        # Blocos opcionais de metadados
        source_line = f'        <dc:source>{xml_escape(meta["source_url"])}</dc:source>' if meta.get("source_url") else ""
        timestamp_line = f'        <meta name="calibre:timestamp" content="{xml_escape(meta["date"])}T00:00:00+00:00"/>' if meta.get("date") else ""
        set_number_line = f'        <meta name="mtg:set_number" content="{xml_escape(meta["set_number"])}"/>' if meta.get("set_number") else ""
        artists_lines = "\n".join(
            f'        <dc:contributor id="ill{i+1}">{xml_escape(a)}</dc:contributor>\n'
            f'        <meta refines="#ill{i+1}" property="role" scheme="marc:relators">ill</meta>'
            for i, a in enumerate(meta.get("artists", []))
        )

        content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:identifier id="BookId">{book_uuid}</dc:identifier>
        <dc:title>{xml_escape(meta['title'])}</dc:title>
        <dc:creator id="creator">{xml_escape(meta['author'])}</dc:creator>
        <meta refines="#creator" property="role" scheme="marc:relators">aut</meta>
        <dc:language>en</dc:language>
        <dc:date>{xml_escape(meta['date'])}</dc:date>
        <dc:publisher>Wizards of the Coast</dc:publisher>
        <dc:rights>&#169; Wizards of the Coast LLC. All rights reserved.</dc:rights>
        <dc:type>Text</dc:type>
        <dc:subject>Fantasy</dc:subject>
        <dc:subject>Magic: The Gathering</dc:subject>
        <dc:subject>Fiction</dc:subject>
{source_line}
{timestamp_line}
{set_number_line}
{artists_lines}
        <meta property="dcterms:modified">{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</meta>

        <!-- Metadados de Coleção / Série EPUB 3 -->
        <meta property="belongs-to-collection" id="c01">{xml_escape(meta['series'])}</meta>
        <meta refines="#c01" property="collection-type">series</meta>
        <meta refines="#c01" property="group-position">{meta['series_index']}</meta>

        <!-- Metadados de Série para Calibre / Kindle / E-readers -->
        <meta name="calibre:series" content="{xml_escape(meta['series'])}"/>
        <meta name="calibre:series_index" content="{meta['series_index']}"/>
        {f'<meta name="cover" content="cover-image"/>' if cover_id else ''}
    </metadata>
    <manifest>
        {"\n        ".join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {"\n        ".join(spine_items)}
    </spine>
</package>"""
        zf.writestr("OEBPS/content.opf", content_opf)

    return True

def convert_set_to_epubs(set_folder: Path, output_base: Path) -> list[Path]:
    """Converte todos os contos de uma coleção em arquivos EPUB individuais ordenados."""
    typ_files = sorted(list(set_folder.glob("*.typ")))
    generated = []
    
    # Filtrar arquivos de resumo de coleção (ex: 064_Reality Fracture.typ na raiz de stories)
    story_files = [f for f in typ_files if re.match(r'^\d{3}_', f.name)]
    if not story_files:
        story_files = [f for f in typ_files if not f.name.endswith("_Reality Fracture.typ")]
        
    set_out = output_base / set_folder.name
    set_out.mkdir(parents=True, exist_ok=True)
    
    for sf in story_files:
        epub_name = sf.with_suffix(".epub").name
        out_epub = set_out / epub_name
        print(f"Gerando EPUB: {sf.name} -> {out_epub.name}")
        if build_epub_for_story(sf, out_epub):
            generated.append(out_epub)
            
    return generated

def combine_set_to_single_epub(set_folder: Path, output_epub_path: Path) -> bool:
    """Gera um único volume consolidado EPUB para a coleção inteira com todos os episódios."""
    typ_files = sorted([f for f in set_folder.glob("*.typ") if re.match(r'^\d{3}_', f.name)])
    if not typ_files:
        return False
        
    first_meta = extract_metadata_from_typ(typ_files[0])
    set_title = first_meta["set_name"]
    
    # Buscar capa: primeira imagem do primeiro episódio ou da pasta
    cover_image_path = find_cover_image(typ_files[0])
    cover_id = f"cover{cover_image_path.suffix.lower()}" if cover_image_path else None
    
    book_uuid = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_DNS, str(set_folder))}"
    
    manifest_items = [
        '<item id="css" href="styles.css" media-type="text/css"/>',
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
    ]
    spine_items = []
    nav_list = []
    ncx_points = []
    
    if cover_id and cover_image_path:
        cover_mime = mimetypes.guess_type(cover_image_path.name)[0] or "image/jpeg"
        manifest_items.append(f'<item id="cover-image" href="images/{cover_id}" media-type="{cover_mime}" properties="cover-image"/>')
        manifest_items.append('<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>')
        spine_items.append('<itemref idref="cover-page"/>')

    output_epub_path.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(output_epub_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/styles.css", EPUB_CSS)
        
        if cover_id and cover_image_path:
            zf.write(cover_image_path, f"OEBPS/images/{cover_id}")
            cover_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head><title>Cover</title><link rel="stylesheet" type="text/css" href="styles.css"/></head>
<body style="margin:0; padding:0;"><div class="cover-container"><img src="images/{cover_id}" alt="Cover Image"/></div></body>
</html>"""
            zf.writestr("OEBPS/cover.xhtml", cover_xhtml)

        image_counter = 1
        all_authors = set()
        all_artists = set()

        for idx, sf in enumerate(typ_files, start=1):
            meta = extract_metadata_from_typ(sf)
            all_authors.add(meta["author"])
            all_artists.update(meta.get("artists", []))

            
            image_map = {}
            body_xhtml, ref_images = typst_to_xhtml_body(sf.read_text(encoding="utf-8", errors="replace"), sf, image_map)
            
            for img_path in ref_images:
                img_name = f"img_{image_counter:03d}{img_path.suffix.lower()}"
                image_counter += 1
                mime = mimetypes.guess_type(img_path.name)[0] or "image/jpeg"
                zf.write(img_path, f"OEBPS/images/{img_name}")
                manifest_items.append(f'<item id="{img_name.replace(".", "_")}" href="images/{img_name}" media-type="{mime}"/>')
                body_xhtml = body_xhtml.replace(f"images/{image_map.get(img_path, '')}", f"images/{img_name}")
                
            chap_filename = f"chapter_{idx:02d}.xhtml"
            chap_id = f"chap_{idx:02d}"
            
            chap_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
    <title>{xml_escape(meta['title'])}</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <h1 class="story-title">{xml_escape(meta['title'])}</h1>
    <div class="story-meta">
        <span class="author">by {xml_escape(meta['author'])}</span>
        <span class="set-name">{xml_escape(meta['set_name'])} • {xml_escape(meta['date'])}</span>
    </div>
    <div class="story-content">
{body_xhtml}
    </div>
</body>
</html>"""
            zf.writestr(f"OEBPS/{chap_filename}", chap_xhtml)
            manifest_items.append(f'<item id="{chap_id}" href="{chap_filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{chap_id}"/>')
            
            nav_list.append(f'<li><a href="{chap_filename}">{xml_escape(meta["title"])}</a></li>')
            ncx_points.append(f"""<navPoint id="navpoint-{idx}" playOrder="{idx}">
    <navLabel><text>{xml_escape(meta["title"])}</text></navLabel>
    <content src="{chap_filename}"/>
</navPoint>""")

        authors_str = ", ".join(sorted(all_authors)) if all_authors else "Wizards of the Coast"

        # Metadados extras do omnibus
        set_num_match = re.match(r'^(\d+)\s*-', set_folder.name)
        set_number_omni = set_num_match.group(1) if set_num_match else ""
        set_number_line = f'        <meta name="mtg:set_number" content="{xml_escape(set_number_omni)}"/>' if set_number_omni else ""
        artists_lines = "\n".join(
            f'        <dc:contributor id="ill{i+1}">{xml_escape(a)}</dc:contributor>\n'
            f'        <meta refines="#ill{i+1}" property="role" scheme="marc:relators">ill</meta>'
            for i, a in enumerate(sorted(all_artists))
        )

        # Nav XHTML
        nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head><title>Table of Contents</title><link rel="stylesheet" type="text/css" href="styles.css"/></head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>{xml_escape(set_title)} - Table of Contents</h1>
        <ol>
            {"\n            ".join(nav_list)}
        </ol>
    </nav>
</body>
</html>"""
        zf.writestr("OEBPS/nav.xhtml", nav_xhtml)

        # NCX
        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head><meta name="dtb:uid" content="{book_uuid}"/><meta name="dtb:depth" content="1"/></head>
    <docTitle><text>{xml_escape(set_title)}</text></docTitle>
    <navMap>
        {"\n        ".join(ncx_points)}
    </navMap>
</ncx>"""
        zf.writestr("OEBPS/toc.ncx", toc_ncx)

        # Content OPF
        first_date = extract_metadata_from_typ(typ_files[0]).get("date", "") if typ_files else ""
        timestamp_line = f'        <meta name="calibre:timestamp" content="{xml_escape(first_date)}T00:00:00+00:00"/>' if first_date else ""

        content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:identifier id="BookId">{book_uuid}</dc:identifier>
        <dc:title>{xml_escape(set_title)} (Complete Stories)</dc:title>
        <dc:creator id="creator">{xml_escape(authors_str)}</dc:creator>
        <meta refines="#creator" property="role" scheme="marc:relators">aut</meta>
        <dc:language>en</dc:language>
        <dc:publisher>Wizards of the Coast</dc:publisher>
        <dc:rights>&#169; Wizards of the Coast LLC. All rights reserved.</dc:rights>
        <dc:type>Text</dc:type>
        <dc:subject>Fantasy</dc:subject>
        <dc:subject>Magic: The Gathering</dc:subject>
        <dc:subject>Fiction</dc:subject>
{timestamp_line}
{set_number_line}
{artists_lines}
        <meta property="dcterms:modified">{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</meta>

        <!-- Metadados de Coleção / Série EPUB 3 -->
        <meta property="belongs-to-collection" id="c01">{xml_escape(set_title)}</meta>
        <meta refines="#c01" property="collection-type">series</meta>

        <!-- Metadados de Série para Calibre / Kindle / E-readers -->
        <meta name="calibre:series" content="{xml_escape(set_title)}"/>
        <meta name="calibre:series_index" content="1"/>
        {f'<meta name="cover" content="cover-image"/>' if cover_id else ''}
    </metadata>
    <manifest>
        {"\n        ".join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {"\n        ".join(spine_items)}
    </spine>
</package>"""
        zf.writestr("OEBPS/content.opf", content_opf)

    return True

def main():
    parser = argparse.ArgumentParser(description="MTG Stories Typst to EPUB Converter")
    parser.add_argument("--file", type=str, help="Caminho de um arquivo .typ específico para converter em EPUB")
    parser.add_argument("--set", type=str, help="Nome ou pasta de uma coleção (ex: '064 - Reality Fracture' ou 'Reality Fracture')")
    parser.add_argument("--all", action="store_true", help="Converte todas as coleções de histórias em EPUBs")
    parser.add_argument("--combine", action="store_true", help="Gera também um volume único consolidado (Omnibus) para a coleção")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR), help="Diretório de saída para os arquivos EPUB")

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if args.file:
        typ_path = Path(args.file)
        if not typ_path.exists():
            print(f"[Erro] Arquivo não encontrado: {typ_path}")
            sys.exit(1)
        out_epub = output_dir / typ_path.with_suffix(".epub").name
        print(f"Convertendo história: {typ_path.name}")
        build_epub_for_story(typ_path, out_epub)
        print(f"[OK] EPUB gerado com sucesso: {out_epub}")
        return

    if args.set:
        target_dir = None
        for d in STORIES_DIR.iterdir():
            if d.is_dir() and (d.name == args.set or args.set.lower() in d.name.lower()):
                target_dir = d
                break
        if not target_dir:
            print(f"[Erro] Coleção '{args.set}' não encontrada em stories/")
            sys.exit(1)
            
        print(f"Processando coleção: {target_dir.name}")
        epubs = convert_set_to_epubs(target_dir, output_dir)
        print(f"[OK] {len(epubs)} episódios convertidos para EPUB em {output_dir / target_dir.name}")
        
        if args.combine:
            comb_out = output_dir / target_dir.name / f"{target_dir.name} - Complete Stories.epub"
            print(f"Gerando volume consolidado da coleção: {comb_out.name}...")
            combine_set_to_single_epub(target_dir, comb_out)
            print(f"[OK] Volume consolidado gerado: {comb_out}")
        return

    if args.all:
        set_dirs = sorted([d for d in STORIES_DIR.iterdir() if d.is_dir()])
        print(f"Convertendo todas as {len(set_dirs)} coleções de histórias...")
        total_epubs = 0
        for sd in set_dirs:
            epubs = convert_set_to_epubs(sd, output_dir)
            total_epubs += len(epubs)
            if args.combine:
                comb_out = output_dir / sd.name / f"{sd.name} - Complete Stories.epub"
                combine_set_to_single_epub(sd, comb_out)
        print(f"\n[SUCESSO] Total de {total_epubs} arquivos EPUB gerados com sucesso em: {output_dir}")
        return

    # Padrão: converter Reality Fracture como demonstração
    print("Nenhuma opção fornecida. Convertendo episódios da coleção recente '064 - Reality Fracture'...")
    rf_dir = STORIES_DIR / "064 - Reality Fracture"
    if rf_dir.exists():
        epubs = convert_set_to_epubs(rf_dir, output_dir)
        comb_out = output_dir / rf_dir.name / f"{rf_dir.name} - Complete Stories.epub"
        combine_set_to_single_epub(rf_dir, comb_out)
        print(f"\n[OK] {len(epubs)} episódios e 1 volume completo gerados em: {output_dir / rf_dir.name}")

if __name__ == "__main__":
    main()
