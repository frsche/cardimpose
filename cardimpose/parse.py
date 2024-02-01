import re

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

	def convert_page_number(page_number):
		try:
			page_number = int(page_number)
		except ValueError:
			raise ValueError(f"Error parsing page spec \"{spec}\": {page_number} is not an integer.")

		if page_number < 0:
			page_index = page_number + num_pages
		else:
			page_index = page_number - 1

		if page_index < 0 or page_index >= num_pages:
			raise ValueError(f"Error parsing page spec \"{spec}\": page {page_index+1} does not exist in document.")

		return page_index

	pages = []
	for spec_part in spec.split(","):

		# the whole document
		if spec_part == ".":
			pages.extend(range(0, num_pages))

		# a specific page
		elif spec_part.isdigit() or spec_part[0] == "-":
			pages.append(convert_page_number(spec_part))

		# multiple copies of a specific page
		elif len(r := spec_part.split("x")) == 2:
			try:
				factor = int(r[0])
			except ValueError:
				raise ValueError(f"Error parsing page spec\"{spec}\": factor {r[0]} is no integer.")
			if factor < 0:
				raise ValueError(f"Error parsing page spec \"{spec}\": factor {r[0]} can not be negative.")
			page = convert_page_number(r[1])
			pages.extend([page]*factor)

		# a range of pages
		elif len(r := spec_part.split("-")) == 2:
			lb = convert_page_number(r[0])
			ub = convert_page_number(r[1])
			if lb < ub:
				pages.extend(range(lb, ub+1))
			else:
				pages.extend(range(lb, ub-1, -1))
		else:
			raise ValueError(f"Error parsing page spec \"{spec}\".")	
	return pages

def parse_nup(nup):
	s = nup.split("x")
	if len(s) != 2:
		raise ValueError("Give rows and cols separated by an \"x\".")
	rows, cols = s
	try:
		rows = int(rows)
		cols = int(cols)
	except ValueError:
		raise ValueError(f"Could not convert \"{nup}\" to pair of ints.")
	return rows, cols