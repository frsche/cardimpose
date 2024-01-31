from cardimpose.parse import parse_page_spec
import itertools
import unittest

from enum import Enum

class Backside(Enum):
	"""The way the backsides of cards are imposed."""

	SINGLESIDED = 0 # do not generate any backsides
	LAST_PAGE = 1   # every card has the same backside, the last page of the input document
	ALTERNATING = 2 # every card in the input document is immediately followed by its backside

class Mode(Enum):
	"""The way the cards are imposed on the resulting document."""

	DUPLICATES = 0 # Each output page consists of multiple copies of the same card
	SINGLES = 1    # Each card is included once in the output

def split_front_back(pages, backside):
	"""Split the list of pages into two separate lists: all pages describing front sides and all pages
	describing backsides (depending on the value of `Backside`).
	"""

	# Backside.SINGLESIDED does not return any pages for the backs.
	if backside == Backside.SINGLESIDED:
		return pages, []
	# Backside.LAST_PAGE returns everything but the last page for the fronts,
	# and the same number of duplicates of the last page for the backs
	elif backside == Backside.LAST_PAGE:
		if len(pages) <= 2:
			raise RuntimeError("Last-Page doublesided is only possible with for than one input page.")
		return pages[:-1], [pages[-1]]*(len(pages)-1)
	# for Backside.ALTERNATING, we split the pages into even and odd pages.
	elif backside == Backside.ALTERNATING:
		if len(pages) % 2 != 0:
			raise RuntimeError("Alternating doublesided is only possible for even number of pages.")
		odd_pages = pages[0:-1:2]
		even_pages = pages[1::2]
		return odd_pages, even_pages
	else:
		raise ValueError(f"unsupported backside setting: {backside}")

def generate_duplicates(pages, cards_per_page):
	"""Generator which generates groups of pages, each page corresponding to a single output page.
	For Mode.DUPLICATES, this fills the whole page with the same page.
	"""

	for page in pages:
		yield [page]*cards_per_page

def generate_singles(pages, cards_per_page):
	"""Generator which generates groups of pages, each page corresponding to a single output page.
	For Mode.SINGLES, this returns all pages once, grouped into the number of cards per page.
	"""

	page_iterator = iter(pages)
	while len(pages := list(itertools.islice(page_iterator, cards_per_page))) != 0:
		if len(pages) < cards_per_page: pages.extend([None]*(cards_per_page-len(pages)))
		yield pages

def flip_horizontal(pages, cols):
	"""Flips the cards on a single output page horizontally (to align with the front sides)."""

	flipped_pages = []
	pages_iter = iter(pages)
	while col := list(itertools.islice(pages_iter, cols)):
		if len(col) < cols: col.extend([None]*(cols-len(col)))
		flipped_pages.extend(col[::-1])
	return flipped_pages

def generate_layout(pages, rows, cols, mode, backside):
	"""Generates lists of page indices, each list corresponding to the cards on one output page."""

	if mode == Mode.DUPLICATES:
		generator = generate_duplicates
	elif mode == Mode.SINGLES:
		generator = generate_singles
	else:
		raise ValueError(f"unsupported mode: {mode}")

	cards_per_page = rows * cols
	if backside != Backside.SINGLESIDED:
		front, back = split_front_back(pages, backside)
		backsides = generator(back, cards_per_page)
	else:
		front = pages
		backsides = None
	for front_output in generator(front, cards_per_page):
		yield front_output
		if backsides:
			yield flip_horizontal(next(backsides), cols)