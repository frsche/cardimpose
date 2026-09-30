#!/usr/bin/env python
import pymupdf
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
			self.card = pymupdf.open(card_path)
		except RuntimeError as e:
			raise RuntimeError(f"Invalid pdf file \"{card_path}\".")

		if not self.card.is_pdf:
			raise RuntimeError(f"Invalid pdf file \"{card_path}\".")

		# the rotation of each page of the card pdf, which is removed from the pages by `_normalize_page`
		self.rotations = [page.rotation for page in self.card]
		for page in self.card:
			self._normalize_page(page)

		self.pages = range(0, self.card.page_count)

		self.gutter_x = parse_length(CardImpose.DEFAULT_GUTTER)
		self.gutter_y = self.gutter_x

		self.margin_x = parse_length(CardImpose.DEFAULT_MARGIN)
		self.margin_y = self.margin_x

		self.bleed = parse_length(CardImpose.DEFAULT_BLEED)
		self.fixed_bleed = False # whether the bleed was explicitly set by the user

		self.output_size = pymupdf.paper_size(CardImpose.DEFAULT_PAPER_SIZE)

		self.crop_mark_length = parse_length(CardImpose.DEFAULT_CM_LENGTH)
		self.crop_mark_thickness = parse_length(CardImpose.DEFAULT_CM_THICKNESS)
		self.crop_mark_distance = parse_length(CardImpose.DEFAULT_CM_DISTANCE)
		self.fixed_crop_mark_distance = False # whether the distance was explicitly set by the user
		self.crop_mark_no_inner = False
		self.crop_mark_no_smaller_than = parse_length(CardImpose.DEFAULT_CM_NO_SMALLER_THAN)
		self.disable_crop_marks = False

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
		self.fixed_bleed = True
		return self

	def set_pages(self, pagespec):
		""""Set the desired range of pages of the card pdf to impose."""

		self.pages = parse_page_spec(pagespec, self.card.page_count)
		return self

	def set_crop_marks(self, length=None, distance=None, no_inner=None, no_smaller_than=None, thickness=None, disable_crop_marks=None):
		"""Configure the crop marks.

		length: the length of the crop marks.
		distance: the distance of the crop mark from the content.
		no_inner: only draw crop marks around the grid.
		no_smaller_than: hide crop marks that are smaller than the given length.
		thickness: the thickness of the crop marks.
		disable_crop_marks: whether to not insert any crop marks.
		"""

		if length:
			self.crop_mark_length = parse_length(length)
		if distance:
			self.crop_mark_distance = parse_length(distance)
			self.fixed_crop_mark_distance = True
		if no_inner is not None:
			self.crop_mark_no_inner = no_inner
		if no_smaller_than is not None:
			self.crop_mark_no_smaller_than = parse_length(no_smaller_than)
		if thickness is not None:
			self.crop_mark_thickness = parse_length(thickness)
		if disable_crop_marks is not None:
			self.disable_crop_marks = disable_crop_marks
		return self

	def set_page_size(self, size, rotate=False):
		"""Set the size of the resulting document.
		Can be either a paper format (e.g. "A4"), or a tuple of width and height (e.g. ("2cm", "2cm")).
		"""

		# if the size is given as a string, we interpret it as a page format (e.g. "A4")
		# or as a string containing the width and height dimensions
		if type(size) == str:
			format_size = pymupdf.paper_size(size)
			if format_size == (-1,-1):
				self.output_size = parse_tuple(size)
			else:
				self.output_size = format_size
		else:
			# otherwise, we expect a tuple of width and height
			self.output_size = (parse_length(size[0]), parse_length(size[1]))

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

	def fill_page(self) -> pymupdf.Document:
		"""Fill the whole page with as many rows and columns as possible."""
		output = pymupdf.Document()
		rows, cols = self._calculate_nup()
		return self.impose(rows, cols)

	def _normalize_page(self, page):
		"""Reduce the visible area (cropbox) of the page to its bleedbox and remove its rotation.

		`show_pdf_page` only shows the cropbox of a page and does not handle rotated pages,
		so we impose unrotated pages and rotate them ourselves (see `self.rotations`).
		This only modifies our in-memory copy of the card pdf.
		"""

		# according to the pdf specification, the bleedbox is clipped to the cropbox
		box = page.bleedbox & page.cropbox
		page.set_rotation(0)
		page.set_cropbox(box)

	def _card_size(self, page_id) -> tuple[float,float]:
		"""The size of the card on the given page (including bleed), taking its rotation into account."""

		rect = self.card.load_page(page_id).rect
		if self.rotations[page_id] % 180 != 0:
			return (rect.height, rect.width)
		return (rect.width, rect.height)

	def _calculate_nup(self) -> tuple[int,int]:
		cardwidth, cardheight = self._card_size(self.pages[0])
		width, height = self.output_size

		available_width = width - 2 * self.margin_x
		available_height = height - 2 * self.margin_y
		rows = math.floor((available_height - cardheight) / (cardheight + self.gutter_y)) + 1
		cols = math.floor((available_width - cardwidth) / (cardwidth + self.gutter_x)) + 1

		if rows <= 0 or cols <= 0:
			raise RuntimeError("Page is to small to fit any cards.")

		return (rows, cols)

	def _detect_bleed(self, page):
		"""Detect the bleed based on information on the given page in the input pdf."""

		first_page = self.card.load_page(page)
		# after `_normalize_page`, the cropbox is the (clipped) bleedbox
		cardbox = first_page.cropbox
		trimbox = first_page.trimbox
		horizontal_bleed = round((cardbox.width - trimbox.width)/2, 3)
		vertical_bleed = round((cardbox.height - trimbox.height)/2, 3)

		if horizontal_bleed != vertical_bleed:
			raise RuntimeError("Automatically detected horizontal and vertical bleed not equal.")

		return horizontal_bleed


	def impose(self, rows, cols) -> pymupdf.Document:
		"""Impose the card in rows and columns at the center of the document."""

		if rows < 1 or cols < 1:
			raise ValueError("The number of rows and columns must be positive.")

		# if there is no explicit bleed set, try to derive it based on the first page
		bleed = self.bleed
		if not self.fixed_bleed:
			derived_bleed = self._detect_bleed(self.pages[0])
			if derived_bleed > 0:
				bleed = derived_bleed

		# if the crop mark distance is not set explicitly, make it equal to the bleed
		crop_mark_distance = self.crop_mark_distance
		if not self.fixed_crop_mark_distance and bleed > 0:
			crop_mark_distance = bleed

		output = pymupdf.Document()
		for pages in generate_layout(self.pages, rows, cols, self.mode, self.backside):
			outputpage = output.new_page(width=self.output_size[0], height=self.output_size[1])
			self._impose(rows, cols, pages, outputpage, bleed, crop_mark_distance)
		return output

	def _impose(self, rows, cols, pages, outputpage, bleed, crop_mark_distance):
		outputbox = outputpage.mediabox

		# empty slots (None) are left blank, but can also be the first slot on a backside page
		cards = [page_id for page_id in pages if page_id is not None]
		cardwidth, cardheight = self._card_size(cards[0])

		for page_id in cards:
			if self._card_size(page_id) != (cardwidth, cardheight):
				raise RuntimeError("All cards must have the same size.")

		# The center of the resulting page
		center_x = outputbox.x1 / 2
		center_y = outputbox.y1 / 2

		# The coordinates of the top left corner of the top left card on the page
		start_x = center_x - (cols * cardwidth / 2) - ((cols-1) * self.gutter_x / 2)
		start_y = center_y - (rows * cardheight / 2) - ((rows-1) * self.gutter_y / 2)

		if start_x < self.margin_x or start_y < self.margin_y:
			raise RuntimeError("Imposition does not fit page size.")

		if cardwidth / 2 <= bleed or cardheight / 2 <= bleed:
			raise RuntimeError("Bleed too large for card size.")

		for x in range(cols):
			for y in range(rows):

				# The top left corner of the current card on the page
				x_pos = start_x + x * cardwidth + x * self.gutter_x
				y_pos = start_y + y * cardheight + y * self.gutter_y

				# The bounding box of the current card
				rect = pymupdf.Rect(x_pos, y_pos, x_pos + cardwidth, y_pos + cardheight)

				page = pages[y*cols + x]
				if page is not None:
					# the page is normalized, so its cropbox is exactly the card including bleed
					outputpage.show_pdf_page(rect, self.card, page, rotate=-self.rotations[page])

				# Whether the current card in in the top/bottom row, left/right column
				# Used to detect whether crop marks are on the inside of the grid
				is_left_col = x == 0
				is_top_row = y == 0
				is_right_col = x == cols-1
				is_bottom_row = y == rows-1

				# the corners of the actual card where the crop marks point to
				top_left_crop = rect.top_left + (bleed, bleed)
				top_right_crop = rect.top_right + (-bleed, bleed)
				bottom_left_crop = rect.bottom_left + (bleed, -bleed)
				bottom_right_crop = rect.bottom_right + (-bleed, -bleed)

				crop_lines = [
					self.crop_line(top_left_crop, "left", not is_left_col, bleed, crop_mark_distance),
					self.crop_line(top_left_crop, "top", not is_top_row, bleed, crop_mark_distance),
					self.crop_line(top_right_crop, "top", not is_top_row, bleed, crop_mark_distance),
					self.crop_line(top_right_crop, "right", not is_right_col, bleed, crop_mark_distance),
					self.crop_line(bottom_left_crop, "left", not is_left_col, bleed, crop_mark_distance),
					self.crop_line(bottom_left_crop, "bottom", not is_bottom_row, bleed, crop_mark_distance),
					self.crop_line(bottom_right_crop, "right", not is_right_col, bleed, crop_mark_distance),
					self.crop_line(bottom_right_crop, "bottom", not is_bottom_row, bleed, crop_mark_distance),
				]
				for line in crop_lines:
					if line:
						outputpage.draw_line(*line, width=self.crop_mark_thickness)

	def crop_line(self, corner, direction, inner, bleed, distance):
		if inner and self.crop_mark_no_inner or self.disable_crop_marks:
			return

		# the maximal length a cropmark can have on the inside to not bleed into other cards
		inner_max_x = self.gutter_x + 2*bleed - 2*distance
		inner_max_y = self.gutter_y + 2*bleed - 2*distance

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

		p1x = corner.x + x_fact * distance
		p1y = corner.y + y_fact * distance
		p2x = corner.x + x_fact * (distance + length)
		p2y = corner.y + y_fact * (distance + length)

		return ((p1x, p1y), (p2x, p2y))