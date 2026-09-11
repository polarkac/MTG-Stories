# Catálogo de Histórias Faltantes e Mídias Não-Scrappeáveis

Este documento rastreia a cobertura de histórias de **Magic: The Gathering** no repositório, identificando o que já foi extraído pelo scraper, o que permanece pendente e quais obras **não podem ser scrappeadas** por pertencerem a mídias pagas, licenciadas ou audiovisuais (como rastreadas pelo [MTGLore](https://mtglore.com/chronological/)).

---

## 1. Status de Webfiction Oficial (Contos Faltantes)

| ID | Coleção | Título / Episódio | Autor | Data | Status no Repositório |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `rf-episode-01` | Reality Fracture | **Episode 1: Tam, Alive** | Alison Lührs | 2026-08-31 | ✅ Scrappeado |
| `rf-episode-02` | Reality Fracture | **Episode 2: Purge Yourself of Doubt** | Alison Lührs | 2026-09-01 | ✅ Scrappeado |
| `rf-episode-03` | Reality Fracture | **Episode 3: I Can Be Both** | Alison Lührs | 2026-09-02 | ✅ Scrappeado |
| `rf-episode-04` | Reality Fracture | **Episode 4: Oh, Sweetie** | Alison Lührs | 2026-09-03 | ✅ Scrappeado |
| `rf-episode-05` | Reality Fracture | **Episode 5: I Don't Need to Convince You** | Alison Lührs | 2026-09-04 | ✅ Scrappeado |
| `rf-episode-06` | Reality Fracture | **Episode 6: The Man Who Kills His Own Ambition** | Alison Lührs | 2026-09-05 | ✅ Scrappeado |
| `rf-episode-07` | Reality Fracture | **Episode 7: Pick Up the Pieces** | Alison Lührs | 2026-09-08 | ✅ Scrappeado |
| `rf-episode-08` | Reality Fracture | **Episode 8: Keep Your Lids Open** | Alison Lührs | 2026-09-09 | ✅ Scrappeado |
| `rf-episode-09` | Reality Fracture | **Episode 9: Unafraid** | Alison Lührs | 2026-09-10 | ✅ Scrappeado |
| `rf-episode-10` | Reality Fracture | **Episode 10: Happy Birthday** | Alison Lührs | 2026-09-11 | ✅ Scrappeado |
| `duskmourn-its-a-beautiful-day` | Duskmourn: House of Horror | **It's a Beautiful Day** | Mira Grant | 2024-08-31 | ✅ Scrappeado |
| `tarkir-spirits-of-the-abzan` | Tarkir: Dragonstorm | **Spirits of the Abzan** | Izzy Wasserstein | 2026-07-06 | ✅ Scrappeado |

---

## 2. Histórias e Mídias NÃO-SCRAPPEÁVEIS (Fora do Escopo Web / Pagas / Áudio)

Estas obras constam na linha do tempo cronológica do MTGLore, porém **não podem ser extraídas diretamente por web scraping** nem devem ser adicionadas como texto aberto, pelos motivos descritos abaixo:

| Título / Série | Formato Original | Editora / Fonte | Data | Motivo de Incompatibilidade com o Scraper |
| :--- | :--- | :--- | :---: | :--- |
| **Strixhaven: Omens of Chaos** | Romance Comercial / Livro (Hardcover, Ebook, Audiobook) | Random House Worlds | 2026-04-07 | Obra literária comercial protegida por direitos autorais, sem publicação aberta em texto web. |
| **Magic: The Gathering: Untold Stories — Elspeth (#1 a #4)** | História em Quadrinhos (Minissérie em 4 edições) | Dark Horse Comics | 2025-09-17 a 2026-06-03 | Edições impressas/digitais pagas de histórias em quadrinhos canônicas. |
| **Magic: The Gathering: Untold Stories — Jace (#1 a #4)** | História em Quadrinhos (Minissérie em 4 edições) | Dark Horse Comics | 2026-04-01 a 2026-09-2026 | Edições impressas/digitais pagas de quadrinhos sobre as memórias de Jace. |
| **Reality Fracture | The Story So Far with The Magic Story Podcast** | Podcast / Áudio Oficial Exclusivo | Wizards of the Coast | 2026-07-20 | Episódio narrativo de podcast com recapitulação em áudio, sem texto em prosa. |
| **The Legends of Reality Fracture** | Artigo Descritivo de Cards Lendários (Card Lore) | Wizards of the Coast | 2026-09-11 | Artigo descritivo de lendas e cartas da coleção, não um conto em prosa. |

---

## 3. Como Executar o Scraper

```bash
# Scrappear todas as histórias do catálogo:
python scraper.py --all

# Scrappear apenas Reality Fracture:
python scraper.py --rf
```
