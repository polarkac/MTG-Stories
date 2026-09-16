#!/usr/bin/env python3
"""
Slugify do acervo MTG Stories.

Percorre stories/, planeswalkers_guides/ e card_lore/, renomeia pastas e
arquivos para slug canônico ([a-z0-9]+ separado por '-') PRESERVANDO a
extensão de arquivos (.typ, .jpg, .pdf, ...), reescreve as referências
nos .typ e grava dois mapas na raiz do workspace:

  - slug-map.json   -> de -> para (caminhos relativos ao workspace)
  - set-names.json  -> slug do set -> nome legível (metadado)

Ordem de execução (interna):
  1. collect_set_names()        (a partir dos nomes BRUTOS)
  2. plan_renames()             (inclui arquivos e pastas)
  3. apply_renames()            (com retry, rollback e detecção de colisão)
  4. rewrite_typ_references()
  5. grava slug-map.json e set-names.json

Uso:
  python sluggyfy.py --dry-run
  python sluggyfy.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT_DIRS = ("stories", "planeswalkers_guides", "card_lore")
SLUG_MAP_FILE = "slug-map.json"
SET_NAMES_FILE = "set-names.json"

# Regex de prefixo numérico (ex.: "058-", "058 ", "058_")
NUMERIC_PREFIX_RE = re.compile(r"^\d+[-_\s]*")
# Prefixo dos guias (ex.: "Planeswalker's Guide to X", "Planeswalkers Guide to X")
GUIDE_PREFIX_RE = re.compile(r"^planeswalkers?-guide-to-", re.IGNORECASE)

# Extensões que NÃO devem ser slugificadas no stem? Nenhuma — todas preservam.
# Este set existe só para documentar a intenção, caso você queira excluir algumas.
PRESERVED_SUFFIXES: frozenset[str] = frozenset()


# ---------------------------------------------------------------------------
# Slug
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """
    Converte para [a-z0-9]+ separado por '-', sem '-' nas pontas, usando python-slugify.

    IMPORTANTE: se 'name' é um arquivo com extensão, preserva a extensão.
      '058 - Duskmourn- House of Horror.typ' -> '058-duskmourn-house-of-horror.typ'
      '01.jpg'                                -> '01.jpg'
      '058 - Duskmourn- House of Horror'     -> '058-duskmourn-house-of-horror'  (pasta)
    """
    from slugify import slugify as py_slugify
    p = Path(name)
    stem = p.stem
    suffix = p.suffix  # inclui o '.'; vazio se não houver extensão

    clean_stem = stem.replace("'", "").replace("’", "").replace('"', "")
    slug_stem = py_slugify(clean_stem, separator="-", lowercase=True)
    if not slug_stem:
        # Fallback: nome original em minúsculas (evita slug vazio)
        slug_stem = stem.casefold().strip()

    return f"{slug_stem}{suffix.lower()}" if suffix else slug_stem


def _readable_from_raw(folder_name: str) -> str:
    """
    Deriva o nome legível a partir do nome BRUTO (antes do slug):
      "Planeswalker's Guide to Ulgrotha" -> "Ulgrotha"
      "021 - Battle for Zendikar"        -> "Battle for Zendikar"
      "New Phyrexia"                     -> "New Phyrexia"
    """
    cleaned = NUMERIC_PREFIX_RE.sub("", folder_name).strip(" -_")
    # Converte aspas curvas/retas em nada e remove prefixo "planeswalkers guide to"
    cleaned = cleaned.replace("'", "").replace("’", "")
    cleaned = GUIDE_PREFIX_RE.sub("", cleaned).strip(" -_")
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Planejamento e aplicação de renames
# ---------------------------------------------------------------------------

def plan_renames(root: Path) -> list[tuple[Path, Path]]:
    """
    Retorna [(origem, destino)] para pastas e arquivos dentro das ROOT_DIRS
    cujo slug difere do nome atual. Ordenado do mais profundo para o mais raso.
    """
    renames: list[tuple[Path, Path]] = []
    for top in ROOT_DIRS:
        base = root / top
        if not base.exists():
            continue
        for path in sorted(base.rglob("*"), key=lambda p: -len(p.parts)):
            new_name = slugify(path.name)
            if not new_name or new_name == path.name:
                continue
            renames.append((path, path.with_name(new_name)))
    return renames


def _detect_collisions(renames: list[tuple[Path, Path]]) -> list[tuple[Path, Path]]:
    """Filtra renames cujo destino colide com um rename anterior ou já existe."""
    seen: dict[Path, Path] = {}
    kept: list[tuple[Path, Path]] = []
    for src, dst in renames:
        if dst.exists() and dst != src:
            print(f"[COLISÃO] {src.name} -> {dst.name} (destino já existe)", file=sys.stderr)
            continue
        if dst in seen:
            print(f"[COLISÃO] {src.name} -> {dst.name} (já reservado por {seen[dst].name})", file=sys.stderr)
            continue
        seen[dst] = src
        kept.append((src, dst))
    return kept


def _safe_rename(src: Path, dst: Path, retries: int = 4) -> None:
    """Tenta renomear com retry curto (Windows às vezes segura o handle por ms)."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            src.rename(dst)
            return
        except PermissionError as exc:
            last_exc = exc
            time.sleep(0.2 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def apply_renames(
    renames: list[tuple[Path, Path]],
    root: Path,
    dry_run: bool,
) -> tuple[list[tuple[str, str]], list[tuple[Path, str]]]:
    """
    Aplica os renames. Retorna:
      - applied: [(from_rel, to_rel)] — relativos ao workspace
      - failures: [(path, mensagem)]
    """
    renames = _detect_collisions(renames)
    applied: list[tuple[str, str]] = []
    failures: list[tuple[Path, str]] = []
    succeeded: list[tuple[Path, Path]] = []  # para rollback

    for src, dst in renames:
        try:
            rel_src = src.relative_to(root).as_posix()
            rel_dst = dst.relative_to(root).as_posix()
        except ValueError:
            # Fora do root (não deveria acontecer)
            rel_src, rel_dst = src.as_posix(), dst.as_posix()

        if dry_run:
            print(f"[RENAME] {rel_src} -> {dst.name}")
            applied.append((rel_src, rel_dst))
            continue

        try:
            _safe_rename(src, dst)
        except PermissionError:
            msg = (
                f"acesso negado ao renomear '{src.name}' -> '{dst.name}'. "
                "Feche Explorer, VS Code, terminais e antivírus apontando para a pasta."
            )
            print(f"[ERRO] {msg}", file=sys.stderr)
            failures.append((src, msg))
            # Rollback do que já foi feito
            _rollback(succeeded)
            return applied, failures
        except OSError as exc:
            print(f"[ERRO] {rel_src} -> {dst.name}: {exc}", file=sys.stderr)
            failures.append((src, str(exc)))
            _rollback(succeeded)
            return applied, failures

        print(f"[RENAME] {rel_src} -> {dst.name}")
        applied.append((rel_src, rel_dst))
        succeeded.append((src, dst))

    if failures:
        print(f"\n[RESUMO] {len(failures)} item(ns) não puderam ser renomeados.", file=sys.stderr)
    return applied, failures


def _rollback(pairs: list[tuple[Path, Path]]) -> None:
    """Reverte uma lista de (src_original, dst_atual) em ordem inversa."""
    if not pairs:
        return
    print(f"\n[ROLLBACK] revertendo {len(pairs)} rename(s)...", file=sys.stderr)
    for src, dst in reversed(pairs):
        try:
            if dst.exists() and not src.exists():
                dst.rename(src)
                print(f"[ROLLBACK] {dst.name} -> {src.name}", file=sys.stderr)
        except OSError as exc:
            print(f"[ROLLBACK][ERRO] {dst} -> {src}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Coleta de nomes legíveis (ANTES do rename)
# ---------------------------------------------------------------------------

def collect_set_names(root: Path) -> dict[str, str]:
    """
    Mapeia slug do set -> nome legível, usando os nomes BRUTOS atuais.
    Deve ser chamado ANTES de apply_renames.
    """
    result: dict[str, str] = {}

    stories_base = root / "stories"
    if stories_base.exists():
        for folder in stories_base.iterdir():
            if not folder.is_dir():
                continue
            readable = _readable_from_raw(folder.name)
            slug = slugify(readable)
            if slug:
                result[slug] = readable

    for top in ("planeswalkers_guides", "card_lore"):
        base = root / top
        if not base.exists():
            continue
        for folder in base.iterdir():
            if not folder.is_dir():
                continue
            readable = _readable_from_raw(folder.name)
            slug = slugify(readable)
            if slug:
                result.setdefault(slug, readable)

    return result


# ---------------------------------------------------------------------------
# Reescreve referências nos .typ
# ---------------------------------------------------------------------------

def rewrite_typ_references(root: Path, rename_map: dict[str, str], dry_run: bool) -> int:
    """
    Reescreve referências nos .typ com base no mapa real de renames.
    Os caminhos em 'rename_map' são RELATIVOS ao workspace.
    """
    string_map: dict[str, str] = {}
    for old, new in rename_map.items():
        old_parts = Path(old).parts
        new_parts = Path(new).parts
        if len(old_parts) != len(new_parts):
            continue
        # Nome do último componente
        string_map[old_parts[-1]] = new_parts[-1]
        # Sufixos progressivos: "pasta/arquivo", "a/b/arquivo", etc.
        for i in range(2, len(old_parts) + 1):
            old_suffix = "/".join(old_parts[-i:])
            new_suffix = "/".join(new_parts[-i:])
            string_map[old_suffix] = new_suffix

    # Ordena por tamanho decrescente para não substituir pedaços menores antes
    sorted_keys = sorted(string_map.keys(), key=len, reverse=True)

    changed = 0
    for top in ROOT_DIRS:
        base = root / top
        if not base.exists():
            continue
        for typ in base.rglob("*.typ"):
            original = typ.read_text(encoding="utf-8", errors="replace")
            content = original
            for key in sorted_keys:
                if key in content:
                    content = content.replace(key, string_map[key])
            if content != original:
                changed += 1
                print(f"[TYP] {typ.relative_to(root)}")
                if not dry_run:
                    typ.write_text(content, encoding="utf-8")
    return changed


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Slugify do acervo MTG Stories")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true", help="Não escreve nada")
    args = parser.parse_args()

    root: Path = args.root.resolve()
    print(f"Workspace: {root}")

    # 1. Coleta nomes legíveis ANTES de renomear (usa nomes brutos)
    set_names = collect_set_names(root)
    print(f"[SET] {len(set_names)} nome(s) de set coletado(s)")

    # 2. Planeja renames (pastas + arquivos, com extensão preservada)
    renames = plan_renames(root)
    print(f"[PLAN] {len(renames)} rename(s) planejado(s)")
    if not renames:
        print("Nada a renomear.")

    # 3. Aplica (com retry, rollback e colisões)
    applied, failures = apply_renames(renames, root, args.dry_run)

    # 4. Grava slug-map.json (caminhos RELATIVOS)
    slug_map_path = root / SLUG_MAP_FILE
    payload = {
        "version": 1,
        "roots": list(ROOT_DIRS),
        "renames": {old: new for old, new in applied},
    }
    print(f"[MAP] {slug_map_path} ({len(applied)} entradas)")
    if not args.dry_run:
        slug_map_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # 5. Reescreve referências nos .typ
    changed = rewrite_typ_references(root, payload["renames"], args.dry_run)
    print(f"[TYP] {changed} arquivo(s) atualizado(s)")

    # 6. Grava set-names.json
    set_names_path = root / SET_NAMES_FILE
    print(f"[SET] {set_names_path} ({len(set_names)} sets)")
    if not args.dry_run:
        set_names_path.write_text(
            json.dumps(set_names, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if failures:
        print(
            f"\n[FALHA] {len(failures)} rename(s) não aplicado(s). "
            "O acervo foi revertido ao estado anterior. Corrija e rode de novo.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())