# MTG Stories

This is an archive of MTG stories publicly available on Wizard of the Coast website and compiled into PDF version.

Stories are sorted into folders by set names and in published order. I used https://mtglore.com/story-timeline-published-order/ for this.

To download and compile I wrote a small Python script, which is not part this repository.

# Typst

I used [Typst](https://typst.app/) as typesetting system (modern version of LaTeX). Every story has source file `.typ` which can be used to compile your own PDF.

You can use web app - though I do not know how to work with own packages in web app - or better to use CLI version of Typst which you can download from https://github.com/typst/typst

Folder `typst_packages` has a small package `mtgstory` under `local` namespace which is used as base setting for all the stories. If you want to use it, you have to put it in your Typst package directory:

Windows: `%APPDATA/typst/packages/`  
Linux: `~/.local/share/typst/packages/`

More info can be found https://github.com/typst/packages#local-packages
