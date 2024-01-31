# Cardimpose

Cardimpose is a Python library that makes it easy to arrange multiple copies of a PDF on a larger document, perfect for scenarios like printing business cards. The library lets you customize your layout while adding crop marks and comes with a handy command line tool.

## Examples

### Business Cards

<details>
<summary>Show Example</summary>

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

The example card actually has a 3mm bleed around the edges.
When informing `cardimpose`, it positions the cut marks accordingly:

`$ cardimpose --gutter 5mm --bleed 3mm card.pdf`

![example2.pdf](https://github.com/frsche/cardimpose/blob/main/images/example3.jpg?raw=true)

It is also possible to explicitly set the number of rows and columns:

`$ cardimpose --gutter 30mmx20mm --bleed 3mm --nup 2x2 --rotate-page card.pdf`

![example3.pdf](https://github.com/frsche/cardimpose/blob/main/images/example4.jpg?raw=true)

Customize the paper size, remove inner cut marks, and more:

`$ cardimpose --gutter 5mm --bleed 3mm --page-size A3 --rotate-page --no-inner-cut-marks card.pdf`

![example4.pdf](https://github.com/frsche/cardimpose/blob/main/images/example5.jpg?raw=true)

</details>

### Flash Cards
<details>
<summary>Show Example</summary>

In the first example, we showcased the capability of printing multiple duplicates of a single card onto a larger sheet.
In this example, we explore a scenario where we aim to produce flashcards, each featuring distinct questions and answers, to print one of each pair.
Furthermore, we desire to have the answer printed on the back of the corresponding question.

To achieve the single printing of each card, we utilize the option `--mode singles`.
To implement the printing of answers on the back, we specify `--backside alternating`.
With this configuration, each card in the input document is immediately followed by the back of the corresponding card.
Alternatively, the `--backside last-page` option can be employed, which prints the same backside on each distinct front - useful for situations like printing playing cards where all cards share a common backside.

For the flashcards, we would run the following command:

`$ cardimpose --gutter 5mm --bleed 3mm --mode singles --backside alternating flash_cards.pdf`

Executing this command results in the following output document:

![example5.pdf](https://github.com/frsche/cardimpose/blob/main/images/example6.jpg?raw=true)

Note that the backsides are horizontally flipped to ensure proper alignment when printing them double-sided.
</details>

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
- Specify single page numbers. Negative page numbers are calculated from the back of the document.
- Define page ranges using hyphens: `1-4` = pages 1, 2, 3 and 4.
- Print a single page multiple times: `5x1` = 5 times the first page
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
