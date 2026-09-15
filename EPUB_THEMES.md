# EPUB Themes

The EPUB converter selects a CSS theme from the collection `set_name`. The base CSS remains active for every EPUB, and a thematic stylesheet is appended when a collection matches.

## Implemented Themes

| Theme | Collections |
| --- | --- |
| Panteons e epicos | Theros, Born of the Gods, Journey into Nyx, Theros: Beyond Death, Kaldheim, Amonkhet, Hour of Devastation |
| Fabulas e folclore | Wilds of Eldraine, Lorwyn Eclipsed, Bloomburrow |
| Cyber-tradicao | Kamigawa: Neon Dynasty |
| Horror gotico | Shadows over Innistrad, Eldritch Moon, Innistrad: Midnight Hunt, Innistrad: Crimson Vow |
| Terror analogico | Duskmourn: House of Horror |
| Aventura e expedicoes | Prologue to Battle for Zendikar, Battle for Zendikar, Oath of the Gatewatch, Zendikar Rising, Ixalan, Rivals of Ixalan, Lost Caverns of Ixalan |

Cinzel, EB Garamond, Crimson Text, Unifraktur Maguntia and Merriweather are sourced from Google Fonts and embedded when their TTF files are available under `fonts/`. Old English Text MT, Planet Kosmos, Stranger Back in the Night and VCR OSD Mono are embedded when their ZIP archives are available there. Check each included license or copyright file before redistribution.

## Without A Theme

The following collections currently use only the base EPUB stylesheet:

- Magic 2013
- Return to Ravnica
- Gatecrash
- Dragon's Maze
- Modern Masters
- Magic 2014
- Commander (2013 Edition)
- Born of the Gods
- Duel Decks: Jace vs. Vraska
## Coverage And Font Research

The 64 identified collections now have a thematic stylesheet. Only `Unknown Set` remains intentionally unthemed.

| Theme | Five keywords | Font research and recommendation |
| --- | --- | --- |
| Panteons e epicos | mitologia, marmore, ouro, deuses, epopeia | Cinzel from Google Fonts; EB Garamond as body fallback. |
| Fabulas e folclore | floresta, manuscrito, magia, aldeia, conto | EB Garamond from Google Fonts; Luminari-style fonts from DaFont only after license review. |
| Cyber-tradicao | neon, tecnologia, samurai, assimetria, contraste | Planet Kosmos local; Stranger Back in the Night local; use Google Fonts Orbitron as a redistributable fallback. |
| Horror gotico | corvo, sangue, lua, igreja, necromancia | Old English Text MT local; Crimson Text and Unifraktur Maguntia from Google Fonts. |
| Terror analogico | VHS, estatica, fita, glitch, transcricao | VCR OSD Mono local; Google Fonts Share Tech Mono or IBM Plex Mono as open fallbacks. |
| Aventura e expedicoes | mapa, ruina, deserto, diario, descoberta | Merriweather from Google Fonts; Roboto Slab is a good open alternative. |
| Intriga urbana | guildas, burocracia, arquitetura, investigacao, lei | EB Garamond from Google Fonts; Libre Baskerville for a more official tone. |
| Clans e dragões | clãs, dragões, honra, guerra, caligrafia | Noto Serif from Google Fonts; Noto Serif TC can support an East Asian brush-adjacent fallback. |
| Horror biomecanico | oleo, metal, invasao, compleacao, assimetria | Cinzel from Google Fonts; Rajdhani or Space Grotesk for a colder technical fallback. |
| Historia de Dominaria | imperio, artefato, mapa, cronica, bronze | Cinzel and Merriweather from Google Fonts. |
| Revolucao de Kaladesh | eter, engrenagem, cobre, invenção, rebeliao | Merriweather for body; Google Fonts Rajdhani or Josefin Sans for headings. |
| Intriga de Fiora | corte, assassinato, cartas, luxo, conspiracao | Berkshire Swash from Google Fonts; a decorative courtly display face. |
| Academia de Arcavios | academia, faculdades, pesquisa, tinta, magia | EB Garamond from Google Fonts; Libre Baskerville for institutional text. |
| Ruptura da realidade | brutalismo, fratura, eco, multiverso, instabilidade | Space Grotesk or IBM Plex Sans from Google Fonts; avoid decorative fonts. |
| Art deco de New Capenna | art deco, mafioso, jazz, diamante, luxo | Montserrat from Google Fonts; Riesling on DaFont is a visual reference, not a default embed. |
| Western de Thunder Junction | western, fronteira, duelo, madeira, procurado | Roboto Slab from Google Fonts; Rye is available in Google Fonts; display fonts from DaFont require license review. |
| Corrida de Aetherdrift | velocidade, metal, pista, equipe, combustao | Rajdhani and Audiowide from Google Fonts. |
| Ficcao de Edge | espaco, estrelas, nave, vazio, tecnologia | Space Grotesk and Orbitron from Google Fonts. |
| Origens dos planeswalkers | memoria, biografia, despertar, trauma, identidade | Libre Baskerville and Cinzel from Google Fonts. |
| Pride multiversal | comunidade, cor, celebracao, identidade, afeto | Quicksand and Nunito Sans from Google Fonts; use color in accents, not as the only contrast cue. |
| Antologia | variedade, editorial, arquivo, personagens, colecao | Cinzel for headings and EB Garamond for body, both already downloaded from Google Fonts. |

Google Fonts pages were used as the primary source because the catalog is open-source and provides license information. DaFont is useful for discovering display styles, but its license varies by author; those fonts should not be embedded without checking the individual license.

### Remaining Unstyled Collection

- Unknown Set
- Edge of Eternities
