#let conf(set_name, doc) = {
    set document(title: set_name)

    [
        #set text(size: 24pt)
        #set align(center + horizon)
        #heading(level: 1)[#set_name]
    ]

    doc
}
