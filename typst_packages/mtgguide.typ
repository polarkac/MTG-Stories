#let conf(
    title,
    date: datetime(day: 05, month: 08, year: 1993),
    author: "Unknown author",
    doc
) = {
    let header = [
        #grid(
            columns: (1fr, 1fr),
            gutter: 2em,
            [*#title*],
            align(right)[*#author*],
        )
        #line(length: 100%)
    ]
    let footer = [
        #align(center)[#context counter(page).display("1")]
        #{
            set align(center)
            set text(fill: gray)
            [All guides at #link("github.com/polarkac/MTG-Stories")]
        }
    ]
    let with_images = sys.inputs.at("with_images", default: "true")
    show figure: it => if with_images == "true" { it }
    set document(title: title, author: author, date: date)
    set par(justify: true)
    set page(paper: "a4", header: header, header-ascent: 15%, footer: footer, margin: (top: 3.0cm))
    [
        #{
            set align(center)
            par(spacing: 2.00em)[#text(size: 3.5em, weight: "bold")[#title]]
            par()[#text(size: 2.5em)[#author]]
        }
        #{
            set text(size: 1.5em)
            set align(center)
            [#date.display("[day]. [month]. [year]")]
        }
        #set figure(supplement: none, numbering: none)
        #set image(height: 40%)
        #set heading(outlined: false)

        #doc
    ]
}
