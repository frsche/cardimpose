import fitz
import re
import math

# parse the length with unit and return the apprioriate length in pixel
def parse_length(length):
	match = re.fullmatch(r"(\d+(?:\.\d*)?)\s*(\w+)", length)
	if match:
		number = float(match.group(1))
		unit = match.group(2)
		if unit == "mm":
			# 25.4 mm per inch, pdf has 72 pixel per inch
			return number / 25.4 * 72
		elif unit == "in":
			return number * 72
	print(f"Error parsing unit {length}")
	exit(1)

class CardImpose:
	def __init__(self, card_path):
		self.card = fitz.open(card_path)
		if self.card.page_count != 1:
			print("Card pdf can only have on page")
			exit(1)
		self.cardpage = self.card.load_page(0)	
		self._cardwidth = self.cardpage.mediabox.width
		self._cardheight = self.cardpage.mediabox.height

		self.gutter_x = parse_length("5mm")
		self.gutter_y = self.gutter_x

		self.margin_x = parse_length("10mm")
		self.margin_y = self.margin_x

		self.bleed = 0
		self.output_size = fitz.paper_size("A4")

		self.crop_mark_length = parse_length("3mm")
		# self.crop_mark_thickness = parse_length("0.1mm")
		self.crop_mark_distance = parse_length("2mm")
		self.crop_mark_no_inner = False
		self.crop_mark_no_smaller_than = parse_length("0.5mm")

	def fill_page(self):
		(width, height) = self.output_size
		available_width = width - 2 * self.margin_x
		available_height = height - 2 * self.margin_y
		rows = math.floor((available_height - self._cardheight) / (self._cardheight + self.gutter_y)) + 1
		cols = math.floor((available_width - self._cardwidth) / (self._cardwidth + self.gutter_x)) + 1
		self.impose(rows, cols)


	def impose(self, rows, cols):
		output = fitz.Document()
		outputpage = output.new_page(width=self.output_size[0], height=self.output_size[1])

		outputbox = outputpage.mediabox

		center_x = outputbox.x1 / 2
		center_y = outputbox.y1 / 2

		start_x = center_x - (cols * self._cardwidth / 2) - ((cols-1) * self.gutter_x / 2)
		start_y = center_y - (rows * self._cardheight / 2) - ((rows-1) * self.gutter_y / 2)

		if start_x < self.margin_x or start_y < self.margin_y:
			print("Imposition does not fit page size")
			exit(1)

		for x in range(cols):
			for y in range(rows):
				x_pos = start_x + x * self._cardwidth + x * self.gutter_x
				y_pos = start_y + y * self._cardheight + y * self.gutter_y

				rect = fitz.Rect(x_pos, y_pos, x_pos + self._cardwidth, y_pos + self._cardheight)
				outputpage.show_pdf_page(rect, self.card, 0)

				is_left_col = x == 0
				is_top_row = y == 0
				is_right_col = x == cols-1
				is_bottom_row = y == rows-1

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
						outputpage.draw_line(*line)

		output.save("out.pdf")

	def crop_line(self, corner, direction, inner):
		if inner and self.crop_mark_no_inner:
			return

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

		if inner:
			length = min(inner_max, self.crop_mark_length)
		else:
			length = self.crop_mark_length
		if length <= 0 or (self.crop_mark_no_smaller_than and length < self.crop_mark_no_smaller_than):
			return

		p1x = corner.x + x_fact * self.crop_mark_distance
		p1y = corner.y + y_fact * self.crop_mark_distance
		p2x = corner.x + x_fact * (self.crop_mark_distance + length)
		p2y = corner.y + y_fact * (self.crop_mark_distance + length)

		return ((p1x, p1y), (p2x, p2y))


impose = CardImpose("test.pdf")
impose.bleed = parse_length("2mm")
impose.fill_page()
