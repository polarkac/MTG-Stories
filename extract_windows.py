#!/usr/bin/env python3
"""
MTG Stories Windows Extractor
=============================
Extrai todos os 4.889 arquivos do acervo (PDFs, .typ, imagens) do banco Git para o disco Windows,
convertendo automaticamente o caractere proibido ':' (dois-pontos) em '-' (hífen) em nomes
de arquivos e pastas, e ajustando os caminhos internos de include/image nos arquivos Typst.
"""

import os
import sys
import re
import subprocess
import tarfile
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent
PRESERVE_FILES = {
    "scraper.py",
    "MISSING_STORIES.md",
    "scraped_manifest.json"
}

def sanitize_segment(segment: str) -> str:
    from slugify import slugify as py_slugify
    p = Path(segment)
    clean_stem = p.stem.replace("'", "").replace("’", "").replace('"', "")
    if p.suffix:
        stem = py_slugify(clean_stem, separator="-", lowercase=True)
        return f"{stem}{p.suffix.lower()}"
    return py_slugify(clean_stem, separator="-", lowercase=True)

def sanitize_path_string(path_str: str) -> str:
    """Normaliza cada segmento do caminho com python-slugify, separando palavras por hífen."""
    prefix = ""
    if path_str.startswith("./"):
        prefix = "./"
        path_str = path_str[2:]
    elif path_str.startswith("../"):
        prefix = "../"
        path_str = path_str[3:]

    parts = path_str.split("/")
    sanitized_parts = []
    for part in parts:
        if part in (".", "..", ""):
            sanitized_parts.append(part)
        else:
            sanitized_parts.append(sanitize_segment(part))
    return prefix + "/".join(sanitized_parts)

def update_typst_includes_and_images(content: str) -> str:
    """Atualiza referências a caminhos em #include e image(...) para caminhos normalizados."""
    def fix_image(m):
        prefix = m.group(1)
        raw_path = m.group(2)
        clean_path = raw_path.strip("\"'").replace('"', '').replace("'", "").replace("’", "")
        fixed_path = sanitize_path_string(clean_path)
        return f'{prefix}"{fixed_path}"'

    def fix_include(m):
        prefix = m.group(1)
        raw_path = m.group(2)
        clean_path = raw_path.strip("\"'").replace('"', '').replace("'", "").replace("’", "")
        fixed_path = sanitize_path_string(clean_path)
        return f'{prefix}"{fixed_path}"'

    # Corrige image("...") mesmo com aspas quebradas no meio do caminho
    content = re.sub(r'(image\s*\(\s*)(["\'].*?\.(?:jpg|jpeg|png|webp)["\'])', fix_image, content, flags=re.IGNORECASE)

    # Corrige #include "..." mesmo com aspas quebradas no meio do caminho
    content = re.sub(r'(#include\s+)(["\'].*?\.typ["\'])', fix_include, content, flags=re.IGNORECASE)

    return content

def extract_all():
    print(f"Iniciando extração do acervo Git para: {WORKSPACE_DIR}")
    cmd = ["git", "archive", "--format=tar", "HEAD"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=WORKSPACE_DIR)

    total_extracted = 0
    colon_fixed = 0

    with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
        for member in tar:
            raw_name = member.name
            
            # Pular arquivos que criamos recentemente e que não devem ser sobrescritos
            if raw_name in PRESERVE_FILES:
                continue
                
            clean_rel = sanitize_path_string(raw_name)
            target_path = WORKSPACE_DIR / Path(clean_rel)
            
            if ":" in raw_name:
                colon_fixed += 1
                
            if member.isdir():
                target_path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Ler dados do arquivo do stream tar
                f_in = tar.extractfile(member)
                if f_in is None:
                    continue
                file_bytes = f_in.read()
                
                # Se for arquivo Typst, ajusta includes e referências de imagens
                if target_path.suffix.lower() == ".typ":
                    try:
                        text = file_bytes.decode("utf-8")
                        updated_text = update_typst_includes_and_images(text)
                        with open(target_path, "w", encoding="utf-8") as f_out:
                            f_out.write(updated_text)
                    except Exception:
                        with open(target_path, "wb") as f_out:
                            f_out.write(file_bytes)
                else:
                    with open(target_path, "wb") as f_out:
                        f_out.write(file_bytes)
                        
                total_extracted += 1
                if total_extracted % 250 == 0:
                    print(f"[Progresso] {total_extracted} arquivos extraídos (ajustados {colon_fixed} caminhos com dois-pontos)...")

    proc.wait()
    print(f"\n[SUCESSO] Extração concluída!")
    print(f"Total de arquivos extraídos para o disco: {total_extracted}")
    print(f"Total de arquivos/pastas adaptados para o Windows: {colon_fixed}")

if __name__ == "__main__":
    extract_all()
