#!/usr/bin/env python3
"""
Typst to EPUB Converter for MTG Stories (Powered by Pandoc)
===========================================================
Converte arquivos Typst em EPUB usando o motor do Pandoc para 
garantir conformidade total com o padrão EpubCheck.

Melhorias:
- Delegação do parseamento de body para a AST do Pandoc.
- Injeção dinâmica de metadados compatíveis com Calibre (Dublin Core).
- Conversão automática de capas WebP para JPEG (compatibilidade Kindle/E-readers antigos).
- Sumários (TOC) reais e quebras de página por capítulo.
"""

import os
import sys
import re
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

ROOT_DIR = Path(__file__).resolve().parent
STORIES_DIR = ROOT_DIR / "stories"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "epubs"

# CSS Aprimorado para E-readers
EPUB_CSS = """
@charset "utf-8";
body {
    font-family: "Bookerly", Georgia, "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.45;
    margin: 3% 5%;
    color: #1a1a1a;
    background-color: #fafafa;
    text-align: justify;
    -webkit-hyphens: auto;
    hyphens: auto;
}

/* Força quebra de página antes de novos capítulos */
h1 {
    page-break-before: always;
    font-size: 1.8em;
    line-height: 1.25;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    text-align: center;
    font-weight: bold;
}

h2 { font-size: 1.35em; margin-top: 1.5em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }
h3 { font-size: 1.15em; margin-top: 1.2em; }

p { margin-top: 0; margin-bottom: 0; text-indent: 1.5em; }
p.first-p, h1 + p, h2 + p, h3 + p, hr + p, blockquote + p { text-indent: 0; margin-top: 1em; }

blockquote {
    margin: 1.2em 1em;
    padding: 0.5em 1em;
    border-left: 4px solid #555;
    background-color: #f7f7f7;
    font-style: italic;
}
blockquote p { text-indent: 0; margin-bottom: 0.5em; }

hr {
    border: none;
    text-align: center;
    margin: 2em 0;
    height: 1.5em;
}
hr:before {
    content: "*  *  *";
    color: #555;
    font-size: 1.2em;
    letter-spacing: 0.5em;
}

figure { margin: 1.5em 0; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; height: auto; border-radius: 4px; }
figcaption { font-size: 0.85em; color: #555; margin-top: 0.5em; font-style: italic; }
"""

def extract_metadata_from_typ(file_path: Path) -> dict:
    """Extrai metadados usando as regras de fallback estabelecidas (Resiliente a formatação)."""
    content = file_path.read_text(encoding="utf-8", errors="replace")
    
    # Extrações via Regex Flexível
    title_match = re.search(r'conf\s*\(\s*["\'](.*?)["\']\s*,', content, re.DOTALL)
    set_match = re.search(r'set_name:\s*["\']([^"\']+)["\']', content)
    author_match = re.search(r'author:\s*["\']([^"\']+)["\']', content)
    date_match = re.search(r'(?:story_)?date:\s*datetime\s*\(\s*day:\s*(\d+),\s*month:\s*(\d+),\s*year:\s*(\d+)\s*\)', content)

    # Fallbacks 
    clean_name = re.sub(r'^\d+[\s_-]*', '', file_path.stem)
    title = title_match.group(1).strip() if title_match and title_match.group(1) != "Untitled" else clean_name.replace('-', ': ')
    
    parent_name = re.sub(r'^\d+[\s_-]*', '', file_path.parent.name).strip(' -')
    set_name = set_match.group(1).strip() if set_match else (parent_name or "Magic: The Gathering Stories")
    
    author = author_match.group(1).strip() if author_match else "Wizards of the Coast"

    if date_match:
        story_date = f"{int(date_match.group(3)):04d}-{int(date_match.group(2)):02d}-{int(date_match.group(1)):02d}"
    else:
        story_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    num_match = re.match(r'^(\d+)', file_path.stem)
    series_index = int(num_match.group(1)) if num_match else 1
    
    set_num_match = re.match(r'^(\d+)\s*-', file_path.parent.name)
    set_number = set_num_match.group(1) if set_num_match else ""

    return {
        "title": title,
        "set_name": set_name,
        "author": author,
        "date": story_date,
        "series": set_name,
        "series_index": series_index,
        "set_number": set_number,
        "file_path": file_path
    }

def process_cover_image(typ_path: Path, temp_dir: Path) -> Path | None:
    """Busca a capa e converte WEBP para JPEG se necessário para segurança no Kindle."""
    cand_dirs = [
        typ_path.parent / typ_path.stem,
        typ_path.parent / "images",
        typ_path.parent
    ]
    
    for d in cand_dirs:
        if d.exists() and d.is_dir():
            imgs = sorted(list(d.glob("*.jpg")) + list(d.glob("*.jpeg")) + list(d.glob("*.png")) + list(d.glob("*.webp")))
            if imgs:
                img_path = imgs[0]
                # Se for webp e tivermos Pillow, converte em tempo real
                if img_path.suffix.lower() == ".webp" and HAS_PIL:
                    safe_cover = temp_dir / "safe_cover.jpg"
                    with Image.open(img_path) as im:
                        im.convert("RGB").save(safe_cover, "JPEG")
                    return safe_cover
                return img_path
    return None

def sanitize_typst_for_pandoc(content: str) -> str:
    """Remove macros específicas do MTGStory e normaliza separadores para o Pandoc entender."""
    # Remove imports e conf block
    clean = re.sub(r'#import\s+["\'][^"\']+["\'].*?(?=#show|\Z)', '', content, flags=re.DOTALL)
    clean = re.sub(r'#show:\s*doc\s*=>\s*conf\s*\([^)]*\)\s*', '', clean, flags=re.DOTALL)
    
    # Transforma macros de cena do Typst em Horizontal Rules reais (---)
    clean = re.sub(r'#line\(.*?\)', '---', clean)
    clean = re.sub(r'#v\([^)]+\)', '', clean)
    
    return clean

def generate_calibre_metadata_xml(meta: dict, temp_dir: Path) -> Path:
    """Gera XML extra injetável no Pandoc para séries no Calibre/EPUB3."""
    xml_content = f"""
    <meta name="calibre:series" content="{xml_escape(meta['series'])}"/>
    <meta name="calibre:series_index" content="{meta['series_index']}"/>
    <meta property="belongs-to-collection" id="c01">{xml_escape(meta['series'])}</meta>
    <meta refines="#c01" property="collection-type">series</meta>
    <meta refines="#c01" property="group-position">{meta['series_index']}</meta>
    """
    xml_path = temp_dir / "calibre_meta.xml"
    xml_path.write_text(xml_content, encoding="utf-8")
    return xml_path

def run_pandoc(input_files: list[Path], output_epub: Path, meta: dict, cover: Path | None, is_omnibus: bool = False):
    """Orquestra a chamada de subprocesso para o Pandoc com as melhores práticas de EPUB."""
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        
        # 1. Preparar CSS
        css_path = temp_dir / "styles.css"
        css_path.write_text(EPUB_CSS, encoding="utf-8")
        
        # 2. Preparar XML de metadados
        xml_meta_path = generate_calibre_metadata_xml(meta, temp_dir)

        # 3. Limpar os arquivos Typst e salvar na pasta temp
        clean_inputs = []
        resource_paths = set()
        
        for idx, typ_file in enumerate(input_files):
            clean_content = sanitize_typst_for_pandoc(typ_file.read_text(encoding="utf-8", errors="replace"))
            
            # Se for Omnibus, injetamos um Título de Capítulo H1 explícito caso o arquivo não tenha
            if is_omnibus and not clean_content.strip().startswith("="):
                sub_meta = extract_metadata_from_typ(typ_file)
                clean_content = f"= {sub_meta['title']}\n\n" + clean_content

            temp_typ = temp_dir / f"clean_{idx:03d}.typ"
            temp_typ.write_text(clean_content, encoding="utf-8")
            clean_inputs.append(temp_typ)
            
            # Necessário para o Pandoc encontrar as imagens referenciadas nos contos originais
            resource_paths.add(str(typ_file.parent))
            resource_paths.add(str(typ_file.parent / "images"))

        # 4. Construir Comando Pandoc
        output_epub.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "pandoc",
            "-f", "typst",
            "-t", "epub3",
            "-o", str(output_epub),
            "--css", str(css_path),
            "--epub-metadata", str(xml_meta_path),
            "--toc", "--toc-depth=2",
            "--split-level=1",
            "--resource-path", ":".join(resource_paths),
            "--metadata", f"title={meta['title']}",
            "--metadata", f"creator={meta['author']}",
            "--metadata", f"date={meta['date']}",
            "--metadata", f"publisher=Wizards of the Coast",
            "--metadata", f"lang=en-US"
        ]

        if cover:
            cmd.extend(["--epub-cover-image", str(cover)])
            
        cmd.extend([str(p) for p in clean_inputs])

        # Executar subprocesso
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[Erro no Pandoc] Falha ao processar {output_epub.name}:\n{e.stderr}")
            return False

def build_epub_for_story(typ_path: Path, output_epub_path: Path) -> bool:
    meta = extract_metadata_from_typ(typ_path)
    with tempfile.TemporaryDirectory() as td:
        cover = process_cover_image(typ_path, Path(td))
        return run_pandoc([typ_path], output_epub_path, meta, cover, is_omnibus=False)

def combine_set_to_single_epub(set_folder: Path, output_epub_path: Path) -> bool:
    typ_files = sorted([f for f in set_folder.glob("*.typ") if re.match(r'^\d{3}_', f.name)])
    if not typ_files:
        return False
        
    first_meta = extract_metadata_from_typ(typ_files[0])
    omnibus_meta = {
        "title": f"{first_meta['set_name']} (Complete Stories)",
        "author": "Wizards of the Coast",  # Volumes combinados geralmente usam a publicadora/vários autores
        "date": first_meta['date'],
        "series": first_meta['set_name'],
        "series_index": 1
    }
    
    with tempfile.TemporaryDirectory() as td:
        cover = process_cover_image(typ_files[0], Path(td))
        return run_pandoc(typ_files, output_epub_path, omnibus_meta, cover, is_omnibus=True)

# As funções convert_set_to_epubs e a main() permanecem virtualmente idênticas 
# ao seu código original para manter a integração do CLI intocada.

def convert_set_to_epubs(set_folder: Path, output_base: Path) -> list[Path]:
    typ_files = sorted([f for f in set_folder.glob("*.typ") if re.match(r'^\d{3}_', f.name)])
    set_out = output_base / set_folder.name
    generated = []
    for sf in typ_files:
        out_epub = set_out / sf.with_suffix(".epub").name
        print(f"Gerando: {out_epub.name}")
        if build_epub_for_story(sf, out_epub):
            generated.append(out_epub)
    return generated

def main():
    parser = argparse.ArgumentParser(description="MTG Stories Typst to EPUB Converter (Pandoc)")
    parser.add_argument("--file", type=str, help="Caminho de um arquivo .typ específico")
    parser.add_argument("--set", type=str, help="Nome/pasta de uma coleção")
    parser.add_argument("--combine", action="store_true", help="Gera Omnibus consolidado")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)

    # Validar Pandoc
    try:
        subprocess.run(["pandoc", "-v"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("[Erro Crítico] Pandoc não encontrado. Instale-o e adicione-o ao PATH.")
        sys.exit(1)

    if args.file:
        typ_path = Path(args.file)
        out_epub = output_dir / typ_path.with_suffix(".epub").name
        build_epub_for_story(typ_path, out_epub)
        print(f"[OK] EPUB gerado: {out_epub}")
    elif args.set:
        target_dir = next((d for d in STORIES_DIR.iterdir() if args.set.lower() in d.name.lower()), None)
        if target_dir:
            convert_set_to_epubs(target_dir, output_dir)
            if args.combine:
                combine_set_to_single_epub(target_dir, output_dir / target_dir.name / f"{target_dir.name} - Omnibus.epub")
        else:
            print(f"[Erro] Coleção '{args.set}' não encontrada.")
    else:
        print("Forneça --file ou --set. (Ex: --set '064 - Reality Fracture' --combine)")

if __name__ == "__main__":
    main()