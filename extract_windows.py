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

def sanitize_path_string(path_str: str) -> str:
    """Substitui dois-pontos proibidos no Windows por hífen em cada segmento do caminho."""
    parts = path_str.split("/")
    sanitized_parts = []
    for part in parts:
        clean = part.replace(":", "-")
        # Evitar pontos ou espaços no fim de nomes de pasta/arquivo no Windows
        if clean not in (".", ".."):
            clean = clean.strip()
        sanitized_parts.append(clean)
    return "/".join(sanitized_parts)

def update_typst_includes_and_images(content: str) -> str:
    """Atualiza referências a caminhos com ':' dentro de arquivos .typ para '-'."""
    def fix_include(m):
        prefix = m.group(1)
        path = m.group(2)
        fixed_path = path.replace(":", "-")
        return f'{prefix}"{fixed_path}"'

    # Corrige #include "..."
    content = re.sub(r'(#include\s+)(["\'][^"\']+["\'])', lambda m: f'{m.group(1)}"{m.group(2)[1:-1].replace(":", "-")}"', content)
    
    # Corrige image("...")
    content = re.sub(r'(image\s*\(\s*)(["\'][^"\']+["\'])', lambda m: f'{m.group(1)}"{m.group(2)[1:-1].replace(":", "-")}"', content)
    
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
