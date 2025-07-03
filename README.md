# MTG Stories

This is an archive of MTG stories publicly available on Wizard of the Coast website and compiled into PDF version. Images are also available either in PDF or as a separate files.

Stories are sorted into folder `stories` by set name and in published order.

Stories from Magic 2013 to Modern Masters 2015 are sorted with https://mtg.wiki/page/Magic_Story.  
Stories from Magic Origins to March of the Machine: The Aftermath are sorted with https://mtglore.com/chronological/.  
Stories from Wilds of Eldraine going forward sorted with https://mtgstory.com

To download and compile I wrote a small Python script, which is not part this repository.

If you want to download all the PDFs or complete stories in one big file (with or without images), use https://github.com/polarkac/MTG-Stories/releases  
If you want to compile all stories into one big PDF yourself, use Typst source file `COMPLETE_STORIES.typ`.

# List of sets (in published order)

- Magic 2013
- Return to Ravnica
- Gatecrash
- Dragon's Maze
- Modern Masters
- Magic 2014
- Theros
- Commander (2013 Edition)
- Born of the Gods
- Duel Decks: Jace vs. Vraska
- Journey info Nyx
- Conspiracy
- Magic 2015
- Khans of Tarkir
- Commander (2014 Edition)
- Fate Reforged
- Dragons of Tarkir
- Modern Masters 2015
- Magic Origins
- Prologue to Battle for Zendikar
- Battle for Zendikar
- Commander (2015 Edition)
- Oath of the Gatewatch
- Shadows Over Innistrad
- Eternal Masters
- Eldritch Moon
- Conspiracy: Take the Crown
- Kaladesh
- Aether Revolt
- Amonkhet
- Hour of Devastation
- Ixalan
- Rivals of Ixalan
- Dominaria
- Core 2019
- Guilds of Ravnica
- Ravnica Allegiance
- War of the Spark
- Throne of Eldraine
- Theros: Beyond Death
- Ikoria: Lair of Behemoths
- Zendikar Rising
- Kaldheim
- Strixhaven: School of Mages
- Innistrad: Midnight Hunt
- Innistrad: Crimson Vow
- Kamigawa: Neon Dynasty
- Streets of New Capenna
- Pride Across the Multiverse
- Dominaria United
- The Brothers’ War
- Phyrexia: All Will Be One
- March of the Machine
- March of the Machine: The Aftermath
- Wilds of Eldraine
- Lost Caverns of Ixalan
- Murders at Karlov Manor
- Outlaws of Thunder Junction
- Bloomburrow
- Duskmourn: House of Horror
- Aetherdrift
- Tarkir: Dragonstorm
- Edge of Eternities

# Typst

I used [Typst](https://typst.app/) as typesetting system (modern version of LaTeX). Every story has source file `.typ` which can be used to compile your own PDF.

## Compiling

First you must move the directories inside `typst_packages` into package directory based on OS. If the directory does not exist, create it.

Windows: `%APPDATA/typst/packages/`  
Linux: `~/.local/share/typst/packages/`  
MacOS: `~/Library/Application Support/typst/packages/`

Download latest release of Typst https://github.com/typst/typst/releases for your OS. It is command line tool, so you will have to have some knowledge to use it. Also you might want to add Typst executable to your system PATH variable.

After all that you can use `typst` command to compile the source file into PDF. Switch to a directory where `stories` directory is.

`cd /home/polarkac/mtgstory`

And to compile:

`typst compile "stories/042 - Strixhaven: School of Mages/001_Episode 1: Class Is in Session.typ"`

This will create compiled PDF beside the Typst source file with a same name.

# Contribution

If you find any mistake or you want to contribute, feel free to send a pull request. You can also contact me at mtg@pohlreichlukas.eu.
