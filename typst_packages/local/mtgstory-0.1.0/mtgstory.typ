#let conf(title, set_name: "Unknown set", author: "Unknown author", show_images: true, doc) = {
    set par(justify: true)
    set page(
        paper: "a4",
        header: [
            #grid(
                columns: (1fr, 1fr),
                gutter: 2em,
                [*#title\ by #author*],
                align(right)[*#set_name*],
            )
            #line(length: 100%)
        ],
        footer: [
            #align(center)[#counter(page).display("1")]
        ],
    )
    [
        #set document(title: title, author: author)
        #{
            set text(size: 2.5em)
            set align(center)
            heading(level: 2, title)
            author
        }
        #{
            set text(size: 1.5em)
            set align(center)
            [From set #emph[#set_name]]
        }
        #set heading(outlined: false)

        #if show_images == false [
            #show figure: it => {}
            #doc
        ] else [
            #doc
        ]
    ]
}
