# Cardimpose

A python library to impose multiple copies of a pdf onto a larger document.

## Example

Assume we want to print the following buisness card `card.pdf`:

With the `cardimpose` command line tool, it is easy to print multiple copies of this card onto a larger sheet while adding crop marks.

`$ cardimpose card.pdf`

By default the cards a put next to each other, filling the whole document.

However, we can also specify the distance between the cards:

`$cardimpose --gutter 5mm card.pdf`

This adds a 5mm gap between the cards:

Actually, the card contains a 4mm bleed around the edge.
When informing `cardimpose`, it positions the cut marks accordingly.

`$cardimpose --gutter 5mm --bleed 4mm card.pdf`

It is also possible to explicitly set the number of rows and columns:

`$cardimpose --gutter 5mmx10mm --bleed 4mm --nup 2x2 --rotate-page card.pdf`

We can specify the paper size and remove the cut marks inside the grid:

`$cardimpose --gutter 5mm --bleed 4mm --page-size A3 --no-inner-cut-marks card.pdf`