# Cardimpose

Cardimpose is a Python library that makes it easy to arrange multiple copies of a PDF on a larger document, perfect for scenarios like printing business cards. The library lets you customize your layout while adding crop marks and comes with a handy command line tool.

## Example

Lets say you have a buisness card named `card.pdf`:

![card.pdf](https://github.com/frsche/cardimpose/blob/main/images/card.jpg?raw=true)

With the `cardimpose.py` command line tool, it is easy to print multiple copies of this card onto a larger sheet while adding crop marks:

`$ cardimpose.py card.pdf`

By default, the cards a placed side by side on an A4 sheet, filling up the entire document:

![example0.pdf](https://github.com/frsche/cardimpose/blob/main/images/example1.jpg?raw=true)

However, it is possible to tweak the layout.
In the following example, we add a 5mm gap between the cards:

`$ cardimpose.py --gutter 5mm card.pdf`

![example1.pdf](https://github.com/frsche/cardimpose/blob/main/images/example2.jpg?raw=true)

The example card actually has a 4mm bleed around the edges.
When informing `cardimpose`, it positions the cut marks accordingly:

`$ cardimpose.py --gutter 5mm --bleed 4mm card.pdf`

![example2.pdf](https://github.com/frsche/cardimpose/blob/main/images/example3.jpg?raw=true)

It is also possible to explicitly set the number of rows and columns:

`$ cardimpose.py --gutter 5mmx10mm --bleed 4mm --nup 2x2 --rotate-page card.pdf`

![example3.pdf](https://github.com/frsche/cardimpose/blob/main/images/example4.jpg?raw=true)

Customize the paper size, remove inner cut marks, and more:

`$ cardimpose.py --gutter 5mm --bleed 4mm --page-size A3 --no-inner-cut-marks card.pdf`

![example4.pdf](https://github.com/frsche/cardimpose/blob/main/images/example5.jpg?raw=true)