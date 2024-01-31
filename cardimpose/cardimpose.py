#!/usr/bin/env python
import fitz
import math

from cardimpose.parse import parse_length, parse_tuple, parse_page_spec
from cardimpose.layout import Mode, Backside, generate_layout

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
	DEFAULT_MODE = Mode.DUPLICATES
	DEFAULT_BACKSIDE = Backside.SINGLESIDED


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

		self.mode = CardImpose.DEFAULT_MODE
		self.backside = CardImpose.DEFAULT_BACKSIDE

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

	def set_mode(self, mode):
		"""Set the card mode of the resulting document.
		Can be either Mode.DUPLICATES or Mode.SINGELS	
		"""

		self.mode = mode
		return self

	def set_backside(self, backside):
		"""Set the kind of backsides generated in the resulting document.
		Can be either Backside.SINGLESIDED, Backside.LAST_PAGE or Backside.ALTERNATING
		"""

		self.backside = backside
		return self

	def fill_page(self) -> fitz.Document:
		"""Fill the whole page with as many rows and columns as possible."""
		output = fitz.Document()
		rows, cols = self.calculate_nup()
		return self.impose(rows, cols)

	def calculate_nup(self) -> (int,int):
		card_page = self.card.load_page(self.pages[0])
		cardwidth, cardheight = card_page.mediabox.width, card_page.mediabox.height
		width, height = self.output_size

		available_width = width - 2 * self.margin_x
		available_height = height - 2 * self.margin_y
		rows = math.floor((available_height - cardheight) / (cardheight + self.gutter_y)) + 1
		cols = math.floor((available_width - cardwidth) / (cardwidth + self.gutter_x)) + 1

		if rows <= 0 or cols <= 0:
			raise RuntimeError("Page is to small to fit any cards.")

		return (rows, cols)

	def impose(self, rows, cols) -> fitz.Document:
		"""Impose the card in rows and columns at the center of the document."""
		output = fitz.Document()
		for pages in generate_layout(self.pages, rows, cols, self.mode, self.backside):
			outputpage = output.new_page(width=self.output_size[0], height=self.output_size[1])
			self._impose(rows, cols, pages, outputpage)
		return output

	def _impose(self, rows, cols, pages, outputpage):
		outputbox = outputpage.mediabox
		card_page = self.card.load_page(pages[0])
		cardwidth, cardheight = card_page.mediabox.width, card_page.mediabox.height

		for page_id in pages:
			page = self.card.load_page(page_id)
			if page.mediabox.width != cardwidth or page.mediabox.height != cardheight:
				raise RuntimeError("All cards must have the same size.")

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

				page = pages[y*cols + x]
				if page is not None:
					outputpage.show_pdf_page(rect, self.card, page)

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