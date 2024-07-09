#let conf(
    title,
    set_name: "Unknown set",
    story_date: datetime(day: 05, month: 08, year: 1993),
    author: "Unknown author",
    doc
) = {
    let header = [
        #grid(
            columns: (1fr, 1fr),
            gutter: 2em,
            [*#title\ by #author*],
            align(right)[*#set_name*],
        )
        #line(length: 100%)
    ]
    let footer = [
        #align(center)[#counter(page).display("1")]
        #{
            set align(center)
            set text(fill: gray)
            [All stories at #link("github.com/polarkac/MTG-Stories")]
        }
    ]

    set document(title: title, author: author, date: story_date)
    set par(justify: true)
    set page(paper: "a4", header: header, header-ascent: 15%, footer: footer, margin: (top: 3.0cm))
    [
        #{
            set text(size: 2.5em)
            set align(center)
            heading(level: 2, title)
            author
        }
        #{
            set text(size: 1.5em)
            set align(center)
            [From set #emph[#set_name]\ #story_date.display("[day]. [month]. [year]")]
        }
        #set heading(outlined: false)
        #doc
    ]
}
