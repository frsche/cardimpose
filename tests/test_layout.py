from cardimpose.layout import *

class LayoutGeneratorTest(unittest.TestCase):
	def test_duplicate_singlesided(self):
		pages = parse_page_spec("1-4", 4)
		layout = list(generate_layout(pages, 2, 2, Mode.DUPLICATES, Backside.SINGLESIDED))
		self.assertEqual(len(layout), 4) # we generate 4 output pages
		self.assertEqual(layout[0], [0,0,0,0]) # first page is completely with page 1 (index 0)
		self.assertEqual(layout[1], [1,1,1,1]) # and so on
		self.assertEqual(layout[2], [2,2,2,2])
		self.assertEqual(layout[3], [3,3,3,3])

	def test_duplicate_backside_last_page(self):
		pages = parse_page_spec("1-4", 4)
		layout = list(generate_layout(pages, 2, 2, Mode.DUPLICATES, Backside.LAST_PAGE))
		self.assertEqual(len(layout), 6) # we generate 6 pages (pages 1-3, always backed with page 4)
		self.assertEqual(layout[0], [0,0,0,0]) # first page is completely with page 1 (index 0)
		self.assertEqual(layout[1], [3,3,3,3]) # then the backside (page 4)
		self.assertEqual(layout[2], [1,1,1,1]) # then the second page
		self.assertEqual(layout[3], [3,3,3,3]) # then again the backside
		self.assertEqual(layout[4], [2,2,2,2])
		self.assertEqual(layout[5], [3,3,3,3])

	def test_duplicate_backside_alternating(self):
		pages = parse_page_spec("1-4", 4)
		layout = list(generate_layout(pages, 2, 2, Mode.DUPLICATES, Backside.ALTERNATING))
		# with duplicate, it should be the same as with singlesided
		singlesided_layout = list(generate_layout(pages, 2,2, Mode.DUPLICATES, Backside.SINGLESIDED))
		self.assertEqual(layout, singlesided_layout)

	def test_singles_singlesided(self):
		pages = parse_page_spec("1-12", 12)
		layout = list(generate_layout(pages, 2, 2, Mode.SINGLES, Backside.SINGLESIDED))
		self.assertEqual(len(layout), 3) # we generate 3 pages (with 4 cards each)
		self.assertEqual(layout[0], [0,1,2,3])
		self.assertEqual(layout[1], [4,5,6,7])
		self.assertEqual(layout[2], [8,9,10,11])

	def test_singles_backside_last_page(self):
		pages = parse_page_spec("1-9", 9)
		layout = list(generate_layout(pages, 2, 2, Mode.SINGLES, Backside.LAST_PAGE))
		self.assertEqual(len(layout), 4) # we generate 4 pages (two front sides with a corresponding backside)
		self.assertEqual(layout[0], [0,1,2,3])
		self.assertEqual(layout[1], [8,8,8,8]) # backside is always the last page
		self.assertEqual(layout[2], [4,5,6,7])
		self.assertEqual(layout[3], [8,8,8,8])

	def test_singles_backside_alternating(self):
		pages = parse_page_spec("1-8", 8)
		layout = list(generate_layout(pages, 2, 2, Mode.SINGLES, Backside.ALTERNATING))
		self.assertEqual(len(layout), 2)
		self.assertEqual(layout[0], [0,2,4,6])
		self.assertEqual(layout[1], [3,1,7,5]) # the backside is flipped horizontally

	def test_singles_backside_alternating2(self):
		pages = parse_page_spec("1-10", 10)
		layout = list(generate_layout(pages, 2, 2, Mode.SINGLES, Backside.ALTERNATING))
		self.assertEqual(len(layout), 4)
		self.assertEqual(layout[0], [0,2,4,6])
		self.assertEqual(layout[1], [3,1,7,5])
		self.assertEqual(layout[2], [8,None,None,None])
		self.assertEqual(layout[3], [None,9,None,None])

	def test_wrong_format(self):
		pages = parse_page_spec("1-9", 9)
		with self.assertRaises(RuntimeError):
			# alternating needs even number of pages
			layout = list(generate_layout(pages, 2, 2, Mode.SINGLES, Backside.ALTERNATING))