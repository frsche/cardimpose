from cardimpose.cardimpose import CardImpose
from cardimpose.layout import Mode, Backside
from cardimpose.parse import parse_nup

import argparse
import sys
import os

def main():
	parser = argparse.ArgumentParser(
                    prog='cardimpose',
                    description='Impose multiple copies of a card onto a larger page.')

	parser.add_argument("card", metavar="CARD", help="The path of the pdf file containing the card.")
	parser.add_argument("-o", "--output", help="The path where the resulting document is stored.")
	parser.add_argument("-p", "--pages", help="The pages of the card pdf to impose (default: {CardImpose.DEFAULT_PAGE_SPEC}).", default=CardImpose.DEFAULT_PAGE_SPEC)

	layout_group = parser.add_argument_group("Layout", "Configure the layout of the cards onto the resulting document.")
	layout_group.add_argument("--nup", help="The number of rows and columns of cards to include.", default="auto")
	layout_group.add_argument("--page-size", help=f"The size of the resulting document (default: {CardImpose.DEFAULT_PAPER_SIZE}).", default=CardImpose.DEFAULT_PAPER_SIZE)
	layout_group.add_argument("--rotate-page", help="Rotate the resulting document before imposing.", action="store_true")
	layout_group.add_argument("--gutter", help=f"The gutter inserted between cards (default: {CardImpose.DEFAULT_GUTTER}).", default=CardImpose.DEFAULT_GUTTER)
	layout_group.add_argument("--margin", help=f"The margin included around the resulting document. (default: {CardImpose.DEFAULT_MARGIN}).", default=CardImpose.DEFAULT_MARGIN)
	layout_group.add_argument("--bleed", help=f"The amount of bleed included in the card. (default: {CardImpose.DEFAULT_BLEED} or automatically).")
	layout_group.add_argument("--backside", help=f"The kind of backsides generated in the resulting document. (default: singlesided).", choices=["singlesided", "last-page", "alternating"], default="singlesided")
	layout_group.add_argument("--mode", help=f"Whether to generate single card per input page or whole output page.", choices=["duplicates", "singles"], default="duplicates")

	crop_marks_group = parser.add_argument_group("Crop Marks", "Configure the crop marks included around the cards.")
	crop_marks_group.add_argument("--no-crop-marks", action="store_true", help="do not include cropmarks in the resulting document.")
	crop_marks_group.add_argument("--crop-mark-length", help=f"the length of the cropmarks. (default: {CardImpose.DEFAULT_CM_LENGTH}).", default=CardImpose.DEFAULT_CM_LENGTH)
	crop_marks_group.add_argument("--crop-mark-distance", help=f"the distance of the cropmarks form the card. (default: {CardImpose.DEFAULT_CM_DISTANCE} or bleed).")
	crop_marks_group.add_argument("--crop-mark-thickness", help=f"the thickness of the cropmarks. (default: {CardImpose.DEFAULT_CM_THICKNESS}).", default=CardImpose.DEFAULT_CM_THICKNESS)
	crop_marks_group.add_argument("--no-inner-crop-marks", help=f"hide the cropmarks in between the cards.", action="store_true")

	args = parser.parse_args()

	# argparse does not like enums
	if args.mode == "duplicates":
		args.mode = Mode.DUPLICATES
	elif args.mode == "singles":
		args.mode = Mode.SINGLES

	if args.backside == "singlesided":
		args.backside = Backside.SINGLESIDED
	elif args.backside == "last-page":
		args.backside = Backside.LAST_PAGE
	elif args.backside == "alternating":
		args.backside = Backside.ALTERNATING

	try:
		impose = CardImpose(args.card) \
		.set_page_size(args.page_size, rotate=args.rotate_page) \
		.set_gutter(args.gutter) \
		.set_margin(args.margin) \
		.set_crop_marks(
			length=args.crop_mark_length,
			thickness=args.crop_mark_thickness,
			no_inner=args.no_inner_crop_marks
		) \
		.set_pages(args.pages) \
		.set_mode(args.mode) \
		.set_backside(args.backside)

		if args.bleed:
			impose.set_bleed(args.bleed)
		
		if args.crop_mark_distance:
			impose.set_crop_marks(distance=args.crop_mark_distance)

		if args.nup == "auto":
			document = impose.fill_page()
		else:
			rows, cols = parse_nup(args.nup)
			document = impose.impose(rows, cols)

		if not args.output:
			output = os.path.basename(args.card).removesuffix('.pdf') + "_imposed.pdf"
		else:
			output = args.output

		document.save(output)

	except (ValueError, RuntimeError) as e:
		print(f"Error: {e}", file=sys.stderr)
		exit(1)

if __name__ == "__main__":
	main()