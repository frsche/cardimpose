import fitz
import os
import tempfile
import unittest
from cardimpose.cardimpose import CardImpose
from cardimpose.parse import parse_length

WHITE = (255, 255, 255)

def make_card(path, rotation=0, cropbox=None):
	"""Save a card whose bleedbox (10px inside the page) is split into a red left and a blue right half
	with a green strip at the top. Everything outside the bleedbox is magenta and must not be imposed."""

	doc = fitz.open()
	page = doc.new_page(width=220, height=130)
	page.draw_rect(page.rect, fill=(1, 0, 1), width=0)
	page.draw_rect(fitz.Rect(10, 10, 110, 120), fill=(1, 0, 0), width=0)
	page.draw_rect(fitz.Rect(110, 10, 210, 120), fill=(0, 0, 1), width=0)
	page.draw_rect(fitz.Rect(10, 10, 210, 40), fill=(0, 1, 0), width=0)
	page.set_bleedbox(fitz.Rect(10, 10, 210, 120))
	if cropbox:
		page.set_cropbox(cropbox)
	page.set_rotation(rotation)
	doc.save(path)

def render_card(path):
	"""Render the card like a pdf viewer shows it, with the visible area reduced to the bleedbox."""

	page = fitz.open(path).load_page(0)
	page.set_cropbox(page.bleedbox & page.cropbox)
	return page.get_pixmap()

class ResultAnalyzer:
	def __init__(self, doc):
		self.page = doc.load_page(0)
		images = self.page.get_images()
		self.rects = self.page.get_image_rects(images[0])

	def check_rows_cols(self, asserted_rows, asserted_cols):
		row_data = dict()
		for rect in self.rects:
			x,y = rect.top_left
			x,y = round(x,3), round(y, 3)
			if x not in row_data: row_data[x] = set()
			row_data[x].add(y)

		num_cols = len(row_data)
		num_rows = len(row_data[list(row_data)[0]])

		tc = unittest.TestCase()
		for row in row_data:
			tc.assertEqual(len(row_data[row]), num_rows)

		tc.assertEqual(num_rows, asserted_rows)
		tc.assertEqual(num_cols, asserted_cols)
		

	def check_card_size(self, asserted_width, asserted_height):
		sizes = set((round(rect.width,3), round(rect.height, 3)) for rect in self.rects)
		tc = unittest.TestCase()
		tc.assertEqual(len(sizes), 1)
		width, height = list(sizes)[0]
		tc.assertAlmostEqual(width, asserted_width, 3)
		tc.assertAlmostEqual(height, asserted_height, 3)

	def check_format(self, asserted_format, rotated=False):
		actual_size = self.page.mediabox.width, self.page.mediabox.height
		asserted_size = fitz.paper_size(asserted_format)
		if rotated:
			asserted_size = asserted_size[1], asserted_size[0]
		tc = unittest.TestCase()
		tc.assertEqual(actual_size, asserted_size)

	def check_margin(self, margin):
		leftmost = min(rect.top_left[0] for rect in self.rects)
		topmost = min(rect.top_left[1] for rect in self.rects)

		assert leftmost > margin
		assert topmost > margin

		

class TestImpose(unittest.TestCase):

	def test_fill_page(self):
		# card is 85mmx55mm
		doc = CardImpose("tests/card.pdf").fill_page()
		analyzer = ResultAnalyzer(doc)
		# on A4 it is possible to fit 5x2 cards
		analyzer.check_rows_cols(5,2)
		analyzer.check_card_size(parse_length("85mm"), parse_length("55mm"))
		analyzer.check_format("A4")

	def test_impose(self):
		doc = CardImpose("tests/card.pdf").impose(2, 2)
		analyzer = ResultAnalyzer(doc)
		analyzer.check_rows_cols(2,2)
		analyzer.check_card_size(parse_length("85mm"), parse_length("55mm"))

	def test_rotated(self):
		doc = CardImpose("tests/card.pdf") \
			.set_page_size("A4", True) \
			.fill_page()
		analyzer = ResultAnalyzer(doc)
		analyzer.check_rows_cols(3,3)

	def test_page_format(self):
		doc = CardImpose("tests/card.pdf") \
			.set_page_size("A3", True) \
			.fill_page()
		analyzer = ResultAnalyzer(doc)
		analyzer.check_format("A3", True)
	
	def test_margin(self):
		doc = CardImpose("tests/card.pdf") \
			.set_margin("15mm") \
			.fill_page()
		analyzer = ResultAnalyzer(doc)
		analyzer.check_margin(parse_length("15mm"))

	def test_margin2(self):
		doc = CardImpose("tests/card.pdf") \
			.set_margin("15mm") \
			.set_bleed("10mm") \
			.set_gutter("10mm") \
			.fill_page()
		analyzer = ResultAnalyzer(doc)
		analyzer.check_margin(parse_length("15mm"))
		analyzer.check_rows_cols(4,1)

	def test_crop_marks(self):
		with_marks = CardImpose("tests/card.pdf").impose(2, 2)
		without_marks = CardImpose("tests/card.pdf") \
			.set_crop_marks(disable_crop_marks=True) \
			.impose(2, 2)
		self.assertGreater(len(with_marks[0].get_drawings()), len(without_marks[0].get_drawings()))

	def test_crop_mark_settings_are_kept(self):
		impose = CardImpose("tests/card.pdf") \
			.set_crop_marks(no_inner=True, disable_crop_marks=True) \
			.set_crop_marks(distance="1mm")
		self.assertTrue(impose.crop_mark_no_inner)
		self.assertTrue(impose.disable_crop_marks)

	def test_impose_keeps_settings(self):
		impose = CardImpose("tests/card.pdf").set_bleed("3mm")
		impose.impose(1, 1)
		self.assertEqual(impose.crop_mark_distance, parse_length(CardImpose.DEFAULT_CM_DISTANCE))

	def test_invalid_nup(self):
		for rows, cols in [(0, 2), (2, 0), (-1, 2)]:
			with self.assertRaises(ValueError):
				CardImpose("tests/card.pdf").impose(rows, cols)

	def test_rotated_and_cropped_cards(self):
		with tempfile.TemporaryDirectory() as tmp:
			path = os.path.join(tmp, "card.pdf")
			for rotation in (0, 90, 180, 270):
				# the cropbox is either the whole page or smaller than the bleedbox
				for cropbox in (None, fitz.Rect(20, 20, 200, 110)):
					with self.subTest(rotation=rotation, cropbox=cropbox):
						make_card(path, rotation, cropbox)
						expected = render_card(path)
						width, height = expected.width, expected.height

						# impose the card with a 10px border around it
						doc = CardImpose(path) \
							.set_margin("0mm") \
							.set_page_size((f"{width+20}px", f"{height+20}px")) \
							.set_crop_marks(disable_crop_marks=True) \
							.impose(1, 1)
						result = doc.load_page(0).get_pixmap()

						for x in range(5, width, 10):
							for y in range(5, height, 10):
								self.assertEqual(result.pixel(x+10, y+10), expected.pixel(x, y), f"at ({x}, {y})")

						# nothing outside the bleedbox is shown
						for x in range(0, width+20, 10):
							self.assertEqual(result.pixel(x, 5), WHITE)
						for y in range(0, height+20, 10):
							self.assertEqual(result.pixel(5, y), WHITE)