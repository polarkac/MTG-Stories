from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

THEMES_DIR = Path(__file__).resolve().parent / "themes"
DEFAULT_FONTS_DIR = Path(__file__).resolve().parents[1] / "fonts"


@dataclass(frozen=True)
class Theme:
    name: str
    css_file: str
    font_archives: tuple[tuple[str, str], ...] = ()
    font_files: tuple[str, ...] = ()


THEMES = {
    "mythos": Theme("mythos-pantheon", "theme-mythos-pantheon.css", font_files=("Cinzel.ttf",)),
    "fables": Theme("fables", "theme-fables.css", font_files=("CormorantGaramond.ttf",)),
    "neon": Theme(
        "neon-dynasty",
        "theme-neon-dynasty.css",
        (("PlanetKosmos.ttf", "planet_kosmos.zip"), ("StrangerBackInTheNight.ttf", "stranger_back_in_the_night.zip")),
    ),
    "gothic": Theme(
        "gothic",
        "theme-gothic.css",
        (("OldEnglishTextMT.ttf", "Old English Text MT.zip"),),
        ("CrimsonText.ttf", "UnifrakturMaguntia.ttf"),
    ),
    "analog": Theme("analog-horror", "theme-analog-horror.css", (("VCROSDMono.ttf", "vcr_osd_mono.zip"),)),
    "expedition": Theme("expedition", "theme-expedition.css", font_files=("Merriweather.ttf",)),
    "ravnica": Theme("ravnica", "theme-ravnica.css", font_files=("LibreBaskerville.ttf",)),
    "tarkir": Theme("tarkir", "theme-tarkir.css", font_files=("NotoSerif.ttf",)),
    "phyrexian": Theme("phyrexian", "theme-phyrexian.css", font_files=("SpaceGrotesk.ttf",)),
    "dominaria": Theme("dominaria", "theme-dominaria.css", font_files=("AbrilFatface.ttf",)),
    "kaladesh": Theme("kaladesh", "theme-kaladesh.css", font_files=("Rajdhani.ttf",)),
    "fiora": Theme("fiora", "theme-fiora.css", font_files=("BerkshireSwash.ttf",)),
    "arcavios": Theme("arcavios", "theme-arcavios.css", font_files=("EBGaramond.ttf",)),
    "reality": Theme("reality-fracture", "theme-reality-fracture.css", font_files=("IBMPlexSans.ttf",)),
    "new-capenna": Theme("new-capenna", "theme-new-capenna.css", font_files=("Montserrat.ttf",)),
    "thunder-junction": Theme("thunder-junction", "theme-thunder-junction.css", font_files=("Rye.ttf",)),
    "aetherdrift": Theme("aetherdrift", "theme-aetherdrift.css", font_files=("Audiowide.ttf",)),
    "edge": Theme("edge-of-eternities", "theme-edge-of-eternities.css", font_files=("Orbitron.ttf",)),
    "origins": Theme("planeswalker-origins", "theme-planeswalker-origins.css", font_files=("Bitter.ttf",)),
    "pride": Theme("pride", "theme-pride.css", font_files=("Quicksand.ttf",)),
    "anthology": Theme("anthology", "theme-anthology.css", font_files=("CrimsonText.ttf",)),
}


def _normalized(value: str) -> str:
    return " ".join(value.casefold().replace(":", " ").replace("-", " ").split())


def theme_for_set(set_name: str) -> Theme | None:
    name = _normalized(set_name)
    if any(token in name for token in ("theros", "kaldheim", "amonkhet", "born of the gods", "journey into nyx", "hour of devastation")):
        return THEMES["mythos"]
    if "eldraine" in name or "lorwyn" in name or "bloomburrow" in name:
        return THEMES["fables"]
    if "kamigawa" in name and "neon" in name:
        return THEMES["neon"]
    if "innistrad" in name or "eldritch moon" in name:
        return THEMES["gothic"]
    if "duskmourn" in name:
        return THEMES["analog"]
    if "zendikar" in name or "ixalan" in name or "oath of the gatewatch" in name:
        return THEMES["expedition"]
    if "murders at karlov manor" in name or "guilds of ravnica" in name or "ravnica allegiance" in name or name in {"return to ravnica", "gatecrash", "dragon's maze", "war of the spark"}:
        return THEMES["ravnica"]
    if "tarkir" in name or "fate reforged" in name or "dragons of tarkir" in name or "khans of tarkir" in name:
        return THEMES["tarkir"]
    if "phyrexia" in name or "march of the machine" in name:
        return THEMES["phyrexian"]
    if "dominaria" in name or "brothers' war" in name:
        return THEMES["dominaria"]
    if "kaladesh" in name or "aether revolt" in name:
        return THEMES["kaladesh"]
    if "conspiracy" in name:
        return THEMES["fiora"]
    if "strixhaven" in name:
        return THEMES["arcavios"]
    if "reality fracture" in name:
        return THEMES["reality"]
    if "new capenna" in name:
        return THEMES["new-capenna"]
    if "outlaws of thunder junction" in name:
        return THEMES["thunder-junction"]
    if "aetherdrift" in name:
        return THEMES["aetherdrift"]
    if "edge of eternities" in name:
        return THEMES["edge"]
    if "magic origins" in name:
        return THEMES["origins"]
    if "pride across the multiverse" in name:
        return THEMES["pride"]
    if any(token in name for token in ("modern masters", "commander", "magic 2013", "magic 2014", "magic 2015", "core 2019", "duel decks", "eternal masters")):
        return THEMES["anthology"]
    return None


def load_theme_css(theme: Theme | None) -> str:
    if not theme:
        return ""
    return (THEMES_DIR / theme.css_file).read_text(encoding="utf-8")


def prepare_theme_fonts(theme: Theme | None, fonts_dir: Path | None, temp_dir: Path) -> list[Path]:
    if not theme or not fonts_dir or not fonts_dir.exists():
        return []
    destination = temp_dir / "fonts"
    embedded: list[Path] = []
    for font_name in theme.font_files:
        source = fonts_dir / font_name
        if not source.exists():
            continue
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / font_name
        shutil.copyfile(source, target)
        embedded.append(target)
    for target_name, archive_name in theme.font_archives:
        archive_path = fonts_dir / archive_name
        if not archive_path.exists():
            continue
        with ZipFile(archive_path) as archive:
            members = [member for member in archive.namelist() if member.lower().endswith((".ttf", ".otf"))]
            if not members:
                continue
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / target_name
            with archive.open(members[0]) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            embedded.append(target)
    return embedded
