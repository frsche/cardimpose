#!/usr/bin/env python
import argparse
import fitz
import re
import math
import os
import sys

def parse_length(length) -> float:
	"""Parses the given `length` and returns it as a floating point number in pixels."""

	assert(type(length) is str)
	match = re.fullmatch(r"(\d+(?:\.\d*)?)\s*(\w+)", length)
	if match:
		number = float(match.group(1))
		unit = match.group(2).lower()
		if unit == "mm":
			# 25.4 mm per inch, pdf has 72 pixel per inch
			return number / 25.4 * 72
		if unit == "cm":
			return number / 25.4 * 72 * 10
		elif unit == "in":
			return number * 72
		elif unit == "px":
			return number

	raise ValueError(f"Unsupported length \"{length}\".")

def parse_tuple(tup) -> (float, float):
	"""Parses the given argument as a tuple in the form \"AxB\" and returns (A,B) or returns (A, A) if only \"A\" is given."""

	assert(type(tup) is str)
	split = re.split(r"(?<!p)x", tup, maxsplit=1)
	if len(split) == 2:
		return (parse_length(split[0]), parse_length(split[1]))
	else:
		length = parse_length(split[0])
		return (length, length)

def parse_page_spec(spec, num_pages):
	pages = []
	for spec in spec.split(","):
		if spec == ".":
			pages.extend(range(0, num_pages))
		elif spec.isdigit():
			pages.append(int(spec)-1)
		elif spec[0] == "-" and spec[1:].isdigit():
			pages.append(num_pages - int(spec[1:]))
		else:
			r = spec.split("-")
			if len(r) == 2:
				lb = int(r[0])
				ub = int(r[1])
				if lb < ub:
					pages.extend(range(lb-1, ub))
				else:
					pages.extend(range(lb-1, ub-2, -1))
			else:
				raise ValueError(f"Error parsing page spec \"{spec}\".")	

	for page in pages:
		if page < 0 or page >= num_pages:
			raise ValueError(f"Page {page+1} does not exist.")
	return pages
	

class CardImpose:
	DEFAULT_GUTTER = "0mm"
	DEFAULT_MARGIN = "10mm"
	DEFAULT_BLEED = "0mm"
	DEFAULT_PAPER_SIZE = "A4"
	DEFAULT_CM_LENGTH = "5mm"
	DEFAULT_CM_THICKNESS = "0.2mm"
	DEFAULT_CM_DISTANCE = "2mm"
	DEFAULT_CM_NO_SMALLER_THAN = "0.5mm"
	DEFAULT_PAGE_SPEC = "."

	def __init__(self, card_path: str):
		"""Construct a new `CardImpose` to impose the card contained in the `card_path` pdf file."""

		try:
			self.card = fitz.open(card_path)
		except RuntimeError as e:
			raise RuntimeError(f"Invalid pdf file \"{card_path}\".")

		self.pages = range(0, self.card.page_count)

		self.gutter_x = parse_length(CardImpose.DEFAULT_GUTTER)
		self.gutter_y = self.gutter_x

		self.margin_x = parse_length(CardImpose.DEFAULT_MARGIN)
		self.margin_y = self.margin_x

		self.bleed = parse_length(CardImpose.DEFAULT_BLEED)
		self.output_size = fitz.paper_size(CardImpose.DEFAULT_PAPER_SIZE)

		self.crop_mark_length = parse_length(CardImpose.DEFAULT_CM_LENGTH)
		self.crop_mark_thickness = parse_length(CardImpose.DEFAULT_CM_THICKNESS)
		self.crop_mark_distance = parse_length(CardImpose.DEFAULT_CM_DISTANCE)
		self.crop_mark_no_inner = False
		self.crop_mark_no_smaller_than = parse_length(CardImpose.DEFAULT_CM_NO_SMALLER_THAN)

	def set_gutter(self, gutter):
		"""Set both the vertical and horizontal gutter between the cards."""

		(self.gutter_x, self.gutter_y) = parse_tuple(gutter)
		return self

	def set_margin(self, margin):
		"""Set the outer margins of the resulting page."""

		(self.margin_x, self.margin_y) = parse_tuple(margin)
		return self

	def set_bleed(self, bleed):
		"""Set the amount of bleed around the card."""

		self.bleed = parse_length(bleed)
		return self

	def set_pages(self, pagespec):
		""""Set the desired range of pages of the card pdf to impose."""

		self.pages = parse_page_spec(pagespec, self.card.page_count)
		return self

	def set_crop_marks(self, length=None, distance=None, no_inner=False, no_smaller_than=None, thickness=None):
		"""Configure the crop marks.

		length: the length of the crop marks.
		distance: the distance of the crop mark from the content.
		no_inner: only draw crop marks around the grid.
		no_smaller_than: hide crop marks that are smaller than the given length.
		thickness: the thickness of the crop marks.
		"""

		if length:
			self.crop_mark_length = parse_length(length)
		if distance:
			self.crop_mark_distance = parse_length(distance)
		if no_inner is not None:
			self.crop_mark_no_inner = no_inner
		if no_smaller_than is not None:
			self.crop_mark_no_smaller_than = parse_length(no_smaller_than)
		if thickness is not None:
			self.crop_mark_thickness = parse_length(thickness)
		return self

	def set_page_size(self, size, rotate=False):
		"""Set the size of the resulting document.
		Can be either a paper format (e.g. "A4") or a tuple of width and height (e.g. ("2cm", "2cm")).
		"""

		# if the size is given as a string, we interpret it as a page format (e.g. "A4")
		if type(size) == str:
			size = fitz.paper_size(size)
			if size == (-1,-1):
				raise ValueError(f"Unknown paper size \"{size}\".")
			self.output_size = size
		else:
			# otherwise, we expect a tuple of width and height
			self.output_size = parse_tuple(size)

		if rotate:
			self.output_size = (self.output_size[1], self.output_size[0])
		return self

	def fill_page(self) -> fitz.Document:
		"""Fill the whole page with as many rows and columns as possible."""
		output = fitz.Document()
		for pageid in self.pages:
			outputpage = output.new_page(width=self.output_size[0], height=self.output_size[1])
			self._fill_page(pageid, outputpage)
		return output

	def _fill_page(self, pageid, outputpage) -> fitz.Page:

		card_page = self.card.load_page(pageid)
		cardwidth, cardheight = card_page.mediabox.width, card_page.mediabox.height
		width, height = self.output_size

		available_width = width - 2 * self.margin_x
		available_height = height - 2 * self.margin_y
		rows = math.floor((available_height - cardheight) / (cardheight + self.gutter_y)) + 1
		cols = math.floor((available_width - cardwidth) / (cardwidth + self.gutter_x)) + 1
		if rows <= 0 or cols <= 0:
			raise RuntimeError("Page is to small to fit any cards.")
		self._impose(rows, cols, pageid, outputpage)

	def impose(self, rows, cols) -> fitz.Document:
		"""Impose the card in rows and columns at the center of the document."""
		output = fitz.Document()
		for pageid in self.pages:
			outputpage = output.new_page(width=self.output_size[0], height=self.output_size[1])
			self._impose(rows, cols, pageid, outputpage)
		return output

	def _impose(self, rows, cols, pageid, outputpage):
		outputbox = outputpage.mediabox

		card_page = self.card.load_page(pageid)
		cardwidth, cardheight = card_page.mediabox.width, card_page.mediabox.height

		# The center of the resulting page
		center_x = outputbox.x1 / 2
		center_y = outputbox.y1 / 2

		# The coordinates of the top left corner of the top left card on the page
		start_x = center_x - (cols * cardwidth / 2) - ((cols-1) * self.gutter_x / 2)
		start_y = center_y - (rows * cardheight / 2) - ((rows-1) * self.gutter_y / 2)

		if start_x < self.margin_x or start_y < self.margin_y:
			raise RuntimeError("Imposition does not fit page size.")

		if cardwidth / 2 <= self.bleed or cardheight / 2 <= self.bleed:
			raise RuntimeError("Bleed too large for card size.")

		for x in range(cols):
			for y in range(rows):
				# The top left corner of the current card on the page
				x_pos = start_x + x * cardwidth + x * self.gutter_x
				y_pos = start_y + y * cardheight + y * self.gutter_y

				# The bounding box of the current card
				rect = fitz.Rect(x_pos, y_pos, x_pos + cardwidth, y_pos + cardheight)
				outputpage.show_pdf_page(rect, self.card, pageid)

				# Whether the current card in in the top/bottom row, left/right column
				# Used to detect whether crop marks are on the inside of the grid
				is_left_col = x == 0
				is_top_row = y == 0
				is_right_col = x == cols-1
				is_bottom_row = y == rows-1

				# the corners of the actual card where the crop marks point to
				top_left_crop = rect.top_left + (self.bleed, self.bleed)
				top_right_crop = rect.top_right + (-self.bleed, self.bleed)
				bottom_left_crop = rect.bottom_left + (self.bleed, -self.bleed)
				bottom_right_crop = rect.bottom_right + (-self.bleed, -self.bleed)

				crop_lines = [
					self.crop_line(top_left_crop, "left", not is_left_col),
					self.crop_line(top_left_crop, "top", not is_top_row),
					self.crop_line(top_right_crop, "top", not is_top_row),
					self.crop_line(top_right_crop, "right", not is_right_col),
					self.crop_line(bottom_left_crop, "left", not is_left_col),
					self.crop_line(bottom_left_crop, "bottom", not is_bottom_row),
					self.crop_line(bottom_right_crop, "right", not is_right_col),
					self.crop_line(bottom_right_crop, "bottom", not is_bottom_row),
				]
				for line in crop_lines:
					if line:
						outputpage.draw_line(*line, width=self.crop_mark_thickness)

	def crop_line(self, corner, direction, inner):
		if inner and self.crop_mark_no_inner:
			return

		# the maximal length a cropmark can have on the inside to not bleed into other cards
		inner_max_x = self.gutter_x + 2*self.bleed - 2*self.crop_mark_distance
		inner_max_y = self.gutter_y + 2*self.bleed - 2*self.crop_mark_distance

		if direction == "left":
			x_fact = -1
			y_fact = 0
			inner_max = inner_max_x
		elif direction == "right":
			x_fact = 1
			y_fact = 0
			inner_max = inner_max_x
		elif direction == "top":
			x_fact = 0
			y_fact = -1
			inner_max = inner_max_y
		elif direction == "bottom":
			x_fact = 0
			y_fact = 1
			inner_max = inner_max_y

		# if we are on the inside of the grid, the crop marks can not be longer than the maximal space available
		if inner:
			length = min(inner_max, self.crop_mark_length)
		else:
			length = self.crop_mark_length

		# hide cropmarks if not enough space
		if length <= 0 or (self.crop_mark_no_smaller_than and length < self.crop_mark_no_smaller_than):
			return

		p1x = corner.x + x_fact * self.crop_mark_distance
		p1y = corner.y + y_fact * self.crop_mark_distance
		p2x = corner.x + x_fact * (self.crop_mark_distance + length)
		p2y = corner.y + y_fact * (self.crop_mark_distance + length)

		return ((p1x, p1y), (p2x, p2y))

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
	layout_group.add_argument("--bleed", help=f"The amount of bleed included in the card. (default: {CardImpose.DEFAULT_BLEED}).")

	cut_marks_group = parser.add_argument_group("Cut Marks", "Configure the cut marks included around the cards.")
	cut_marks_group.add_argument("--no-cut-marks", action="store_true", help="do not include cutmarks in the resulting document.")
	cut_marks_group.add_argument("--cut-mark-length", help=f"the length of the cutmarks. (default: {CardImpose.DEFAULT_CM_LENGTH}).", default=CardImpose.DEFAULT_CM_LENGTH)
	cut_marks_group.add_argument("--cut-mark-distance", help=f"the distance of the cutmarks form the card. (default: {CardImpose.DEFAULT_CM_DISTANCE} or bleed).")
	cut_marks_group.add_argument("--cut-mark-thickness", help=f"the thickness of the cutmarks. (default: {CardImpose.DEFAULT_CM_THICKNESS}).", default=CardImpose.DEFAULT_CM_THICKNESS)
	cut_marks_group.add_argument("--no-inner-cut-marks", help=f"hide the cutmarks in between the cards.", action="store_true")

	args = parser.parse_args()

	if not args.cut_mark_distance:
		if args.bleed:
			args.cut_mark_distance = args.bleed
		else:
			CardImpose.DEFAULT_CM_DISTANCE

	if not args.bleed:
		args.bleed = CardImpose.DEFAULT_BLEED

	try:
		impose = CardImpose(args.card) \
		.set_page_size(args.page_size, rotate=args.rotate_page) \
		.set_gutter(args.gutter) \
		.set_margin(args.margin) \
		.set_bleed(args.bleed) \
		.set_crop_marks(
			length=args.cut_mark_length,
			distance=args.cut_mark_distance,
			thickness=args.cut_mark_thickness,
			no_inner=args.no_inner_cut_marks
		) \
		.set_pages(args.pages)

		if args.nup == "auto":
			document = impose.fill_page()
		else:
			rows, cols = args.nup.split("x")
			document = impose.impose(int(rows), int(cols))

		if not args.output:
			output = os.path.basename(args.card).removesuffix('.pdf') + "_imposed.pdf"
		else:
			output = args.output

		document.save(output)

	except Exception as e:
		print(f"Error: {e}", file=sys.stderr)
		exit(1)

if __name__ == "__main__":
	main()