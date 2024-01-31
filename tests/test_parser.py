import unittest
from cardimpose.parse import parse_length, parse_tuple, parse_page_spec

class TestPageSpec(unittest.TestCase):

	def test_simple(self):
		spec = "1,3,5,7"
		pages = parse_page_spec(spec, 10)
		self.assertEqual(pages, [0,2,4,6])

	def test_range(self):
		spec = "1-5"
		pages = parse_page_spec(spec, 10)
		self.assertEqual(pages, [0,1,2,3,4])

	def test_all(self):
		spec = "."
		pages = parse_page_spec(spec, 5)
		self.assertEqual(pages, [0,1,2,3,4])

	def test_last_page(self):
		spec = "-1"
		pages = parse_page_spec(spec, 5)
		self.assertEqual(pages, [4])

	def test_reverse(self):
		spec = "5-1"
		pages = parse_page_spec(spec, 5)
		self.assertEqual(pages, [4,3,2,1,0])

	def test_combination(self):
		spec = "1-3,6"
		pages = parse_page_spec(spec, 6)
		self.assertEqual(pages, [0,1,2,5])

	def test_combination2(self):
		spec = "1,1,5-3,."
		pages = parse_page_spec(spec, 5)
		self.assertEqual(pages, [0,0,4,3,2,0,1,2,3,4])

	def test_duplicated_pages(self):
		spec = "10x3"
		pages = parse_page_spec(spec, 5)
		self.assertEqual(pages, [2] * 10)

	def test_duplicated_pages_reverse(self):
		spec = "3x-1"
		pages = parse_page_spec(spec, 5)
		self.assertEqual(pages, [4] * 3)

	def test_duplicated_pages_combination(self):
		spec = "2x1,3x2,1x-1"
		pages = parse_page_spec(spec, 5)
		self.assertEqual(pages, [0,0,1,1,1,4])

	def test_wrong_page(self):
		with self.assertRaises(ValueError):
			parse_page_spec("6", 5)

		with self.assertRaises(ValueError):
			parse_page_spec("1-4", 3)

		with self.assertRaises(ValueError):
			parse_page_spec("-5", 3)
		
		with self.assertRaises(ValueError):
			parse_page_spec("-", 3)

		with self.assertRaises(ValueError):
			parse_page_spec("-2x2", 3)

		with self.assertRaises(ValueError):
			parse_page_spec("0", 3)

class TestParseLength(unittest.TestCase):

	def test_mm(self):
		length = "5mm"
		parsed_length = parse_length(length)
		self.assertEqual(parsed_length, 5/25.4*72)

	def test_cm(self):
		length = "10cm"
		parsed_length = parse_length(length)
		self.assertEqual(parsed_length, 10/25.4*72*10)

	def test_in(self):
		length = "0.25in"
		parsed_length = parse_length(length)
		self.assertEqual(parsed_length, 0.25*72)

	def test_px(self):
		length = "10px"
		parsed_length = parse_length(length)
		self.assertEqual(parsed_length, 10)

	def test_all(self):
		# all of these should be equivalent
		l1 = "10mm"
		l2 = "1cm"
		l3 = "0.39370079in"
		l4 = f"{0.39370079*72}px" # 72 pixels per inch
		parsed_l1 = parse_length(l1)
		parsed_l2 = parse_length(l2)
		parsed_l3 = parse_length(l3)
		parsed_l4 = parse_length(l4)
		self.assertAlmostEqual(parsed_l1, parsed_l2, places=6)
		self.assertAlmostEqual(parsed_l1, parsed_l3, places=6)
		self.assertAlmostEqual(parsed_l1, parsed_l4, places=6)

	def test_tuple(self):
		tup = "10cmx10cm"
		parsed_tup = parse_tuple(tup)
		self.assertEqual(parsed_tup, (parse_length("10cm"), parse_length("10cm")))

	def test_tuple_equals(self):
		tup = "10cm"
		parsed_tup = parse_tuple(tup)
		self.assertEqual(parsed_tup, (parse_length("10cm"), parse_length("10cm")))

	def test_tuple_px(self):
		tup = "10pxx1cm"
		parsed_tup = parse_tuple(tup)
		self.assertEqual(parsed_tup, (parse_length("10px"), parse_length("1cm")))