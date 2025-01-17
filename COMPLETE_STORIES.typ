#let title = [Magic 2013 through Duskmourn: House of Horror - The~Ultimate PDF]

#{
    set text(size: 32pt)
    set align(center + horizon)
    heading(level: 1, outlined: false)[#title]
}
#{
    set align(center)
    set text(size: 18pt)
    [Compiled by Polarkac, last update: #datetime.today().display("[day]. [month]. [year]")]
}

#pagebreak()

#show outline.entry.where(level: 1): it => {
    strong(it)
}
#outline(title: [Contents], indent: 32pt)

#pagebreak()

#show heading.where(level: 1): h => {
    set text(size: 24pt)
    set align(center)
    h.body
}

#include "./stories/001_Magic 2013.typ"
#include "./stories/002_Return to Ravnica.typ"
#include "./stories/003_Gatecrash.typ"
#include "./stories/004_Dragon's Maze.typ"
#include "./stories/005_Modern Masters.typ"
#include "./stories/006_Magic 2014.typ"
#include "./stories/007_Theros.typ"
#include "./stories/008_Commander (2013 Edition).typ"
#include "./stories/009_Born of the Gods.typ"
#include "./stories/010_Duel Decks: Jace vs. Vraska.typ"
#include "./stories/011_Journey into Nyx.typ"
#include "./stories/012_Conspiracy.typ"
#include "./stories/013_Magic 2015.typ"
#include "./stories/014_Khans of Tarkir.typ"
#include "./stories/015_Commander (2014 Edition).typ"
#include "./stories/016_Fate Reforged.typ"
#include "./stories/017_Dragons of Tarkir.typ"
#include "./stories/018_Modern Masters 2015.typ"
#include "./stories/019_Magic Origins.typ"
#include "./stories/020_Prologue to Battle for Zendikar.typ"
#include "./stories/021_Battle for Zendikar.typ"
#include "./stories/022_Commander (2015 Edition).typ"
#include "./stories/023_Oath of the Gatewatch.typ"
#include "./stories/024_Shadows over Innistrad.typ"
#include "./stories/025_Eternal Masters.typ"
#include "./stories/026_Eldritch Moon.typ"
#include "./stories/027_Conspiracy: Take the Crown.typ"
#include "./stories/028_Kaladesh.typ"
#include "./stories/029_Aether Revolt.typ"
#include "./stories/030_Amonkhet.typ"
#include "./stories/031_Hour of Devastation.typ"
#include "./stories/032_Ixalan.typ"
#include "./stories/033_Rivals of Ixalan.typ"
#include "./stories/034_Dominaria.typ"
#include "./stories/035_Core 2019.typ"
#include "./stories/036_Guilds of Ravnica.typ"
#include "./stories/037_Ravnica Allegiance.typ"
#include "./stories/038_War of the Spark.typ"
#include "./stories/039_Theros: Beyond Death.typ"
#include "./stories/040_Zendikar Rising.typ"
#include "./stories/041_Kaldheim.typ"
#include "./stories/042_Strixhaven: School of Mages.typ"
#include "./stories/043_Innistrad: Midnight Hunt.typ"
#include "./stories/044_Innistrad: Crimson Vow.typ"
#include "./stories/045_Kamigawa: Neon Dynasty.typ"
#include "./stories/046_Streets of New Capenna.typ"
#include "./stories/047_Pride Across the Multiverse.typ"
#include "./stories/048_Dominaria United.typ"
#include "./stories/049_The Brothers' War.typ"
#include "./stories/050_Phyrexia: All Will Be One.typ"
#include "./stories/051_March of the Machine.typ"
#include "./stories/052_March of the Machine: The Aftermath.typ"
#include "./stories/053_Wilds of Eldraine.typ"
#include "./stories/054_Lost Caverns of Ixalan.typ"
#include "./stories/055_Murders at Karlov Manor.typ"
#include "./stories/056_Outlaws of Thunder Junction.typ"
#include "./stories/057_Bloomburrow.typ"
#include "./stories/058_Duskmourn: House of Horror.typ"
#include "./stories/059_Aetherdrift.typ"

// FIX: last document set metadata for whole PDF
#set document(title: title)
