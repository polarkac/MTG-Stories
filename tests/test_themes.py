from mtg_epub.themes import theme_for_set


def test_theme_mapping_handles_sanitized_collection_names():
    assert theme_for_set("Theros- Beyond Death").name == "mythos-pantheon"
    assert theme_for_set("Born of the Gods").name == "mythos-pantheon"
    assert theme_for_set("Journey into Nyx").name == "mythos-pantheon"
    assert theme_for_set("Hour of Devastation").name == "mythos-pantheon"
    assert theme_for_set("Shadows over Innistrad").name == "gothic"
    assert theme_for_set("Eldritch Moon").name == "gothic"
    assert theme_for_set("Lost Caverns of Ixalan").name == "expedition"
    assert theme_for_set("Oath of the Gatewatch").name == "expedition"
    assert theme_for_set("Kamigawa- Neon Dynasty").name == "neon-dynasty"
    assert theme_for_set("Return to Ravnica").name == "ravnica"
    assert theme_for_set("Tarkir- Dragonstorm").name == "tarkir"
    assert theme_for_set("Phyrexia- All Will Be One").name == "phyrexian"
    assert theme_for_set("Streets of New Capenna").name == "new-capenna"
    assert theme_for_set("Aetherdrift").name == "aetherdrift"
    assert theme_for_set("Secrets of Strixhaven").name == "arcavios"
    assert theme_for_set("Magic 2013").name == "anthology"


def test_unmapped_collection_uses_base_css():
    assert theme_for_set("Unknown Set") is None
