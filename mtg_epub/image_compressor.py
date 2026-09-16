"""Compressor e otimizador de imagens com Pillow para e-readers."""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageOps

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def _has_meaningful_alpha(image: Image.Image) -> bool:
    """Verifica se uma imagem RGBA/LA possui transparência perceptível."""
    if image.mode not in ("RGBA", "LA"):
        return False
    alpha = image.getchannel("A")
    extrema = alpha.getextrema()
    # Se o valor mínimo de alfa é 255, a imagem é totalmente opaca
    return extrema[0] < 255


def compress_image(
    input_path: Path,
    output_path: Path | None = None,
    max_dim: int = 1400,
    quality: int = 80,
) -> bool:
    """
    Comprime e redimensiona uma imagem mantendo proporção e qualidade para e-readers.

    - Se output_path for None, sobrescreve input_path de forma atômica.
    - Reduz dimensões se exceder max_dim (LANCZOS).
    - Converte WebP e imagens sem transparência para JPEG otimizado.
    - Remove metadados EXIF pesados/desnecessários.
    """
    input_path = Path(input_path)
    output_path = Path(output_path) if output_path is not None else input_path

    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False

    try:
        with Image.open(input_path) as img:
            # Corrige rotação baseada em EXIF antes de manipular
            img = ImageOps.exif_transpose(img)

            # Redimensiona mantendo proporção apenas se ultrapassar max_dim
            orig_w, orig_h = img.size
            if orig_w > max_dim or orig_h > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            has_alpha = _has_meaningful_alpha(img)

            buffer = io.BytesIO()
            if has_alpha and output_path.suffix.lower() == ".png":
                # PNG com transparência genuína
                img.save(buffer, format="PNG", optimize=True)
            else:
                # Converte para RGB e salva como JPEG otimizado
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(
                    buffer,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    progressive=False,
                )

            compressed_bytes = buffer.getvalue()

            # Só sobrescreve se o arquivo compactado for menor ou se mudou dimensões
            orig_size = input_path.stat().st_size if input_path.exists() else 0
            if orig_size == 0 or len(compressed_bytes) < orig_size or (orig_w, orig_h) != img.size:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temp_output = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
                temp_output.write_bytes(compressed_bytes)
                temp_output.replace(output_path)
                return True

            return False
    except Exception as exc:
        print(f"[Compressor][Aviso] Falha ao comprimir {input_path.name}: {exc}", file=sys.stderr)
        return False


def batch_compress_directories(
    directories: Sequence[Path],
    max_dim: int = 1400,
    quality: int = 80,
    verbose: bool = True,
) -> dict:
    """
    Comprime em lote todas as imagens nas pastas especificadas.
    """
    all_images: list[Path] = []
    for d in directories:
        d = Path(d)
        if not d.exists():
            continue
        for ext in SUPPORTED_EXTENSIONS:
            all_images.extend(d.rglob(f"*{ext}"))
            all_images.extend(d.rglob(f"*{ext.upper()}"))

    # Deduplica
    unique_images = sorted(set(all_images))
    total_files = len(unique_images)
    if total_files == 0:
        return {"total": 0, "compressed": 0, "saved_bytes": 0}

    compressed_count = 0
    total_saved_bytes = 0

    iterator = tqdm(unique_images, desc="Comprimindo imagens", unit="img") if (tqdm and verbose) else unique_images

    for img_path in iterator:
        orig_size = img_path.stat().st_size
        changed = compress_image(img_path, max_dim=max_dim, quality=quality)
        if changed:
            compressed_count += 1
            new_size = img_path.stat().st_size
            total_saved_bytes += max(0, orig_size - new_size)

    if verbose:
        saved_mb = total_saved_bytes / (1024 * 1024)
        print(f"[Compressor] Concluído: {compressed_count}/{total_files} imagens otimizadas. Economia: {saved_mb:.2f} MB")

    return {
        "total": total_files,
        "compressed": compressed_count,
        "saved_bytes": total_saved_bytes,
    }


if __name__ == "__main__":
    dirs = [Path(arg) for arg in sys.argv[1:]] if len(sys.argv) > 1 else [Path("stories"), Path("planeswalkers_guides"), Path("card_lore")]
    batch_compress_directories(dirs)
