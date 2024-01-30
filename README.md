# Cardimpose

Cardimpose is a Python library that makes it easy to arrange multiple copies of a PDF on a larger document, perfect for scenarios like printing business cards. The library lets you customize your layout while adding crop marks and comes with a handy command line tool.

## Example

Lets say you have a buisness card named `card.pdf`:

![card.pdf](https://github.com/frsche/cardimpose/blob/main/images/card.jpg?raw=true)

With the `cardimpose` command line tool, it is easy to print multiple copies of this card onto a larger sheet while adding crop marks:

`$ cardimpose card.pdf`

By default, the cards a placed side by side on an A4 sheet, filling up the entire document:

![example0.pdf](https://github.com/frsche/cardimpose/blob/main/images/example1.jpg?raw=true)

However, it is possible to tweak the layout.
In the following example, we add a 5mm gap between the cards:

`$ cardimpose --gutter 5mm card.pdf`

![example1.pdf](https://github.com/frsche/cardimpose/blob/main/images/example2.jpg?raw=true)

The example card actually has a 4mm bleed around the edges.
When informing `cardimpose`, it positions the cut marks accordingly:

`$ cardimpose --gutter 5mm --bleed 4mm card.pdf`

![example2.pdf](https://github.com/frsche/cardimpose/blob/main/images/example3.jpg?raw=true)

It is also possible to explicitly set the number of rows and columns:

`$ cardimpose --gutter 5mmx10mm --bleed 4mm --nup 2x2 --rotate-page card.pdf`

![example3.pdf](https://github.com/frsche/cardimpose/blob/main/images/example4.jpg?raw=true)

Customize the paper size, remove inner cut marks, and more:

`$ cardimpose --gutter 5mm --bleed 4mm --page-size A3 --no-inner-cut-marks card.pdf`

![example4.pdf](https://github.com/frsche/cardimpose/blob/main/images/example5.jpg?raw=true)

## Installation

Install `cardimpose` using pip:

```bash
pip install cardimpose
```

## Settings

### Specifying Pages

Cardimpose generates one complete output page per selected input page.
By default, every input page is selected.
To control which input pages produce outputs, use the `--pages` argument.

This argument supports various options:
- Use `.` to include all pages.
- Specify single page numbers. Negative page numbers are caculated from the back of the document.
- Define page ranges using hyphens.
- Combine multiple page selections with commas.

For instance, using the command `--pages 1,4-6` will impose pages 1,4,5 and 6 of the input document, generating one imposed output page for each selected input page.

Other command line options apply to all input pages.
To specify different bleeds, margins and gutters for different pages, split the input file into different pdf files and impose them separately.

### Specifying Lengths

Lengths are given by a number with a unit.
Currently, supported units are `mm`, `cm`, `in` and `px`.
The arguments `--margin`, `--bleed` and `--gutter` can also receive separate horizontal and vertical lengths, combined by an `x`.
Setting `--margin 1cmx2cm`, sets the left and right margin to 1cm and the top and bottom margin to 2cm.
A single length for these arguments sets both directions to the same value.

### Crop Marks

By default cut marks are inserted around each imposed card.
The distance, length and thickness can be set through command line arguments (see `cardimpose --help`).
Additionally, it is possible to completely disable cutmarks or to hide the cutmarks in the middle of the imposed cards.