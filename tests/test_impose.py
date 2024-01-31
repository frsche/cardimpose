import fitz
import unittest
from cardimpose.cardimpose import CardImpose
from cardimpose.parse import parse_length

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