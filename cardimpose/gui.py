"""A graphical interface for cardimpose with a live preview of the imposed document."""

import argparse
import os
import re
import tkinter as tk
from dataclasses import dataclass, fields
from tkinter import ttk, filedialog, messagebox

import pymupdf

from cardimpose.cardimpose import CardImpose
from cardimpose.layout import Mode, Backside
from cardimpose.parse import parse_length, parse_nup, parse_tuple

MODES = {"duplicates": Mode.DUPLICATES, "singles": Mode.SINGLES}
BACKSIDES = {
	"singlesided": Backside.SINGLESIDED,
	"last-page": Backside.LAST_PAGE,
	"alternating": Backside.ALTERNATING,
}
PAGE_SIZES = ["A4", "A3", "A5", "Letter"]

# settings containing lengths, which get a default unit when entered without one
LENGTH_SETTINGS = ["page_size", "gutter", "margin", "bleed", "crop_mark_length", "crop_mark_distance", "crop_mark_thickness"]
DEFAULT_UNIT = "mm"

# settings which can be left empty, all others are reset to their last valid value when emptied
OPTIONAL_SETTINGS = ["bleed", "crop_mark_distance"]


def add_default_unit(value, unit=DEFAULT_UNIT):
	"""Add `unit` to all plain numbers in a length (e.g. "5") or a pair of lengths (e.g. "5x3mm")."""

	# split like `parse_tuple`, which does not split at the "x" in "px"
	parts = re.split(r"(?<!p)(x)", value, maxsplit=1)
	return "".join(part.strip() + unit if re.fullmatch(r"\d+(?:\.\d*)?", part.strip()) else part for part in parts)


@dataclass
class Settings:
	"""All options of the imposition, with the same meaning and defaults as the command line options."""

	card: str = ""
	pages: str = CardImpose.DEFAULT_PAGE_SPEC
	page_size: str = CardImpose.DEFAULT_PAPER_SIZE
	rotate_page: bool = False
	nup: str = "auto" # "auto" or "ROWSxCOLS"
	gutter: str = CardImpose.DEFAULT_GUTTER
	margin: str = CardImpose.DEFAULT_MARGIN
	bleed: str = "" # empty: detect automatically
	mode: str = "duplicates"
	backside: str = "singlesided"
	crop_marks: bool = True
	crop_mark_length: str = CardImpose.DEFAULT_CM_LENGTH
	crop_mark_distance: str = "" # empty: equal to the bleed
	crop_mark_thickness: str = CardImpose.DEFAULT_CM_THICKNESS
	no_inner_crop_marks: bool = False


def impose(settings: Settings) -> tuple[pymupdf.Document, int, int]:
	"""Impose the card with the given settings, like the command line tool does.
	Returns the resulting document and the number of rows and columns per page."""

	if not settings.card:
		raise ValueError("No card pdf selected.")

	impose = CardImpose(settings.card) \
		.set_page_size(settings.page_size, rotate=settings.rotate_page) \
		.set_gutter(settings.gutter) \
		.set_margin(settings.margin) \
		.set_crop_marks(
			length=settings.crop_mark_length,
			thickness=settings.crop_mark_thickness,
			no_inner=settings.no_inner_crop_marks,
			disable_crop_marks=not settings.crop_marks,
		) \
		.set_pages(settings.pages) \
		.set_mode(MODES[settings.mode]) \
		.set_backside(BACKSIDES[settings.backside])

	if settings.bleed:
		impose.set_bleed(settings.bleed)
	if settings.crop_mark_distance:
		impose.set_crop_marks(distance=settings.crop_mark_distance)

	if settings.nup == "auto":
		rows, cols = impose._calculate_nup()
	else:
		rows, cols = parse_nup(settings.nup)

	return impose.impose(rows, cols), rows, cols


def check_settings(settings: Settings):
	"""Check the settings which do not depend on the card, like `impose` does, and raise a ValueError if one is invalid.
	This allows checking the settings before a card is selected."""

	if pymupdf.paper_size(settings.page_size) == (-1, -1):
		parse_tuple(settings.page_size)
	parse_tuple(settings.gutter)
	parse_tuple(settings.margin)
	for length in (settings.bleed, settings.crop_mark_length, settings.crop_mark_distance, settings.crop_mark_thickness):
		if length:
			parse_length(length)
	if settings.nup != "auto":
		rows, cols = parse_nup(settings.nup)
		if rows < 1 or cols < 1:
			raise ValueError("The number of rows and columns must be positive.")


def default_output_path(card):
	"""The path the imposed document is saved to by default, next to the card."""

	return os.path.join(os.path.dirname(card), os.path.basename(card).removesuffix(".pdf") + "_imposed.pdf")


class App:
	UPDATE_DELAY = 250 # ms after the last change of a setting until the preview is updated
	RENDER_DELAY = 50 # ms after the last resize of the window until the preview is redrawn
	PREVIEW_PADDING = 12

	def __init__(self, root, card=None):
		self.root = root
		self.document = None
		self.error = None
		self.error_source = None # the setting whose change made the settings invalid
		self.last_changed = None
		self.showing_error = False
		self.text_inputs = {} # widget -> name of its setting
		self.page_index = 0
		self.grid_size = None
		self.photo = None # tkinter does not keep a reference to the displayed image
		self.pending_update = None
		self.pending_render = None

		# one tkinter variable per setting, the nup is built from `grid`, `rows` and `cols`
		self.vars = {}
		for field in fields(Settings):
			if field.type is bool:
				self.vars[field.name] = tk.BooleanVar(value=field.default)
			else:
				self.vars[field.name] = tk.StringVar(value=field.default)
		self.vars["grid"] = tk.StringVar(value="auto")
		self.vars["rows"] = tk.StringVar(value="2")
		self.vars["cols"] = tk.StringVar(value="2")
		# the values of the last valid settings, which replace emptied fields
		self.valid_values = {name: var.get() for name, var in self.vars.items()}

		root.title("cardimpose")
		root.geometry("1100x760")
		root.minsize(800, 560)
		self._build()

		for name, var in self.vars.items():
			var.trace_add("write", lambda *_, name=name: self._on_change(name))
		self.vars["grid"].trace_add("write", lambda *_: self._on_grid_changed())
		self.vars["crop_marks"].trace_add("write", lambda *_: self._update_widget_states())
		self.vars["card"].trace_add("write", lambda *_: self._on_card_changed())
		self._update_widget_states()

		if card:
			self.set_card(os.path.abspath(card))

	def _build(self):
		main = ttk.Frame(self.root, padding=8)
		main.pack(fill="both", expand=True)

		sidebar = ttk.Frame(main)
		sidebar.pack(side="left", fill="y", padx=(0, 8))
		self._build_settings(sidebar)

		preview = ttk.Frame(main)
		preview.pack(side="left", fill="both", expand=True)

		self.canvas = tk.Canvas(preview, background="#8a8a8a", highlightthickness=0)
		self.canvas.pack(fill="both", expand=True)
		self.canvas.bind("<Configure>", lambda _: self.schedule_render())

		nav = ttk.Frame(preview, padding=(0, 6, 0, 0))
		nav.pack(fill="x")
		self.prev_button = ttk.Button(nav, text="<", width=3, command=lambda: self.show_page(self.page_index - 1))
		self.prev_button.pack(side="left")
		self.page_label = ttk.Label(nav, text="", width=16, anchor="center")
		self.page_label.pack(side="left", padx=4)
		self.next_button = ttk.Button(nav, text=">", width=3, command=lambda: self.show_page(self.page_index + 1))
		self.next_button.pack(side="left")

	def _build_settings(self, parent):
		card_group = self._group(parent, "Card")
		ttk.Label(card_group, text="File").grid(row=0, column=0, sticky="w", pady=2)
		file_row = ttk.Frame(card_group)
		file_row.grid(row=0, column=1, columnspan=2, sticky="ew", pady=2)
		file_entry = ttk.Entry(file_row, textvariable=self.vars["card"], width=24)
		file_entry.pack(side="left", fill="x", expand=True)
		self._text_input(file_entry, "card")
		ttk.Button(file_row, text="Open...", command=self.open_card).pack(side="left", padx=(4, 0))
		self._entry(card_group, 1, "Pages", "pages", hint=". = all, 1-3,5,2x4")

		layout = self._group(parent, "Layout")
		ttk.Label(layout, text="Page size").grid(row=0, column=0, sticky="w", pady=2)
		page_size = ttk.Combobox(layout, textvariable=self.vars["page_size"], values=PAGE_SIZES, width=12)
		page_size.grid(row=0, column=1, sticky="ew", pady=2)
		self._text_input(page_size, "page_size")
		ttk.Checkbutton(layout, text="Rotate", variable=self.vars["rotate_page"]) \
			.grid(row=0, column=2, sticky="w", padx=(6, 0))

		ttk.Label(layout, text="Grid").grid(row=1, column=0, sticky="w", pady=2)
		ttk.Radiobutton(layout, text="Fill page", value="auto", variable=self.vars["grid"]) \
			.grid(row=1, column=1, columnspan=2, sticky="w")
		fixed = ttk.Frame(layout)
		fixed.grid(row=2, column=1, columnspan=2, sticky="w", pady=2)
		ttk.Radiobutton(fixed, text="Fixed", value="fixed", variable=self.vars["grid"]).pack(side="left")
		self.rows_spinbox = ttk.Spinbox(fixed, from_=1, to=99, width=3, textvariable=self.vars["rows"])
		self.rows_spinbox.pack(side="left", padx=(6, 2))
		ttk.Label(fixed, text="rows x").pack(side="left")
		self.cols_spinbox = ttk.Spinbox(fixed, from_=1, to=99, width=3, textvariable=self.vars["cols"])
		self.cols_spinbox.pack(side="left", padx=2)
		ttk.Label(fixed, text="cols").pack(side="left")
		self._text_input(self.rows_spinbox, "rows")
		self._text_input(self.cols_spinbox, "cols")

		self._entry(layout, 3, "Gutter", "gutter", hint="e.g. 5, 5x2, 0.2in")
		self._entry(layout, 4, "Margin", "margin", hint=f"default unit: {DEFAULT_UNIT}")
		self._entry(layout, 5, "Bleed", "bleed", hint="empty: auto")

		cards = self._group(parent, "Cards")
		self._choice(cards, 0, "Mode", "mode", list(MODES))
		self._choice(cards, 1, "Backside", "backside", list(BACKSIDES))

		marks = self._group(parent, "Crop marks")
		ttk.Checkbutton(marks, text="Draw crop marks", variable=self.vars["crop_marks"]) \
			.grid(row=0, column=0, columnspan=3, sticky="w", pady=2)
		self.crop_mark_widgets = [
			self._entry(marks, 1, "Length", "crop_mark_length"),
			self._entry(marks, 2, "Distance", "crop_mark_distance", hint="empty: bleed"),
			self._entry(marks, 3, "Thickness", "crop_mark_thickness"),
			ttk.Checkbutton(marks, text="Only around the grid", variable=self.vars["no_inner_crop_marks"]),
		]
		self.crop_mark_widgets[-1].grid(row=4, column=0, columnspan=3, sticky="w", pady=2)

		ttk.Button(parent, text="Save PDF...", command=self.save).pack(fill="x", pady=(12, 0), ipady=4)

	def _group(self, parent, title):
		group = ttk.LabelFrame(parent, text=title, padding=8)
		group.pack(fill="x", pady=(0, 8))
		group.columnconfigure(1, weight=1)
		return group

	def _entry(self, parent, row, label, name, hint=None):
		ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2, padx=(0, 8))
		entry = ttk.Entry(parent, textvariable=self.vars[name], width=12)
		entry.grid(row=row, column=1, sticky="ew", pady=2)
		self._text_input(entry, name)
		if hint:
			ttk.Label(parent, text=hint, foreground="gray").grid(row=row, column=2, sticky="w", padx=(6, 0))
		return entry

	def _text_input(self, widget, name):
		"""Register a widget the user types the setting `name` into.
		Its errors are only shown once the user is done typing, i.e. leaves the widget or presses enter."""

		self.text_inputs[widget] = name
		# wait until the focus moved, to know where it went
		widget.bind("<FocusOut>", lambda _: self.root.after_idle(self._on_input_left, widget))
		widget.bind("<Return>", lambda _: self._on_input_done(widget))

	def _choice(self, parent, row, label, name, values):
		ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2, padx=(0, 8))
		ttk.Combobox(parent, textvariable=self.vars[name], values=values, state="readonly", width=12) \
			.grid(row=row, column=1, sticky="ew", pady=2)

	def _on_card_changed(self):
		self.page_index = 0
		card = self.vars["card"].get()
		self.root.title(f"cardimpose - {os.path.basename(card)}" if card else "cardimpose")

	def _on_grid_changed(self):
		# start the fixed grid from the grid that currently fills the page
		if self.vars["grid"].get() == "fixed" and self.grid_size:
			self.vars["rows"].set(str(self.grid_size[0]))
			self.vars["cols"].set(str(self.grid_size[1]))
			# the change was made by the grid choice, not by typing into the fields
			self.last_changed = "grid"
		self._update_widget_states()

	def _update_widget_states(self):
		fixed = self.vars["grid"].get() == "fixed"
		for spinbox in (self.rows_spinbox, self.cols_spinbox):
			spinbox.state(["!disabled"] if fixed else ["disabled"])
		crop_marks = self.vars["crop_marks"].get()
		for widget in self.crop_mark_widgets:
			widget.state(["!disabled"] if crop_marks else ["disabled"])

	def settings(self) -> Settings:
		"""The settings currently entered in the window."""

		values = {field.name: self._value(field.name) for field in fields(Settings)}
		for name in LENGTH_SETTINGS:
			values[name] = add_default_unit(values[name])
		if self._value("grid") == "fixed":
			values["nup"] = f"{self._value('rows')}x{self._value('cols')}"
		return Settings(**values)

	def _value(self, name):
		"""The value of the setting `name`, or its last valid value if the field was emptied."""

		value = self.vars[name].get()
		if isinstance(value, str):
			value = value.strip()
			if not value and name not in OPTIONAL_SETTINGS:
				value = self.valid_values[name]
		return value

	def _on_change(self, name):
		self.last_changed = name
		self.schedule_update()

	def schedule_update(self):
		"""Update the preview once the settings did not change for `UPDATE_DELAY` ms."""

		if self.pending_update:
			self.root.after_cancel(self.pending_update)
		self.pending_update = self.root.after(self.UPDATE_DELAY, self._scheduled_update)

	def _scheduled_update(self):
		self.update_document()
		# errors of text fields are shown once the user is done typing (see `_on_input_done`),
		# errors of all other changes (checkboxes, choices, opening a file) immediately
		if self.last_changed not in self.text_inputs.values():
			self.report_error()

	def _on_input_left(self, widget):
		if self.showing_error:
			# the message box took the focus
			return
		try:
			if self.root.focus_get() is None:
				# the user switched to another application, check once they leave the field within the window
				return
		except KeyError:
			# raised by tkinter while the focus is in the popup list of a combobox
			pass
		self._on_input_done(widget)

	def _on_input_done(self, widget):
		name = self.text_inputs[widget]
		# show the value that is actually used: the last valid one if the field is empty,
		# and with the default unit added to plain numbers
		value = self._value(name)
		if name in LENGTH_SETTINGS:
			value = add_default_unit(value)
		if value != self.vars[name].get():
			self.vars[name].set(value)
		if self.pending_update:
			self.update_document()
		if self.error_source == name:
			self.report_error()

	def report_error(self):
		"""Show the error of the current settings in a message box,
		and move the focus back to the field which caused the error, so that it can be fixed."""

		if not self.error:
			return
		field = next((widget for widget, name in self.text_inputs.items() if name == self.error_source), None)
		self.showing_error = True
		try:
			messagebox.showerror(
				"Invalid settings",
				self.error,
				detail="The preview still shows the last valid settings.",
				parent=self.root,
			)
		finally:
			self.showing_error = False
		if field:
			field.focus_set()
			field.select_range(0, "end")
			field.icursor("end")

	def update_document(self):
		"""Impose the card with the current settings and show the result."""

		if self.pending_update:
			self.root.after_cancel(self.pending_update)
			self.pending_update = None

		values = {name: self._value(name) for name in self.vars}
		try:
			settings = self.settings()
			if settings.card:
				document, rows, cols = impose(settings)
			else:
				check_settings(settings)
				document = None
		except (ValueError, RuntimeError, OSError) as e:
			if not self.error:
				self.error_source = self.last_changed
			self.error = str(e)
			return

		self.error = None
		self.error_source = None
		self.valid_values = values
		if not document:
			return
		self.document = document
		self.grid_size = (rows, cols)
		self.page_index = min(self.page_index, document.page_count - 1)
		self.render()

	def show_page(self, index):
		if self.document and 0 <= index < self.document.page_count:
			self.page_index = index
			self.render()

	def schedule_render(self):
		if self.pending_render:
			self.root.after_cancel(self.pending_render)
		self.pending_render = self.root.after(self.RENDER_DELAY, self.render)

	def render(self):
		"""Draw the current page of the document, scaled to fit the preview area."""

		self.pending_render = None
		self.canvas.delete("all")
		self._update_navigation()
		if not self.document:
			self.canvas.create_text(
				self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
				text="Open a card pdf to start.", fill="white",
			)
			return

		page = self.document[self.page_index]
		width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
		zoom = min(
			(width - 2 * self.PREVIEW_PADDING) / page.rect.width,
			(height - 2 * self.PREVIEW_PADDING) / page.rect.height,
		)
		if zoom <= 0:
			return

		pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
		self.photo = tk.PhotoImage(data=pixmap.tobytes("ppm"))
		x = (width - pixmap.width) // 2
		y = (height - pixmap.height) // 2
		self.canvas.create_image(x, y, image=self.photo, anchor="nw")

	def _update_navigation(self):
		count = self.document.page_count if self.document else 0
		self.page_label.configure(text=f"Page {self.page_index + 1} of {count}" if count else "")
		self.prev_button.state(["!disabled"] if self.page_index > 0 else ["disabled"])
		self.next_button.state(["!disabled"] if self.page_index < count - 1 else ["disabled"])

	def open_card(self):
		card = self.vars["card"].get()
		path = filedialog.askopenfilename(
			parent=self.root,
			title="Open card",
			initialdir=os.path.dirname(card) if card else os.getcwd(),
			filetypes=[("PDF files", "*.pdf"), ("All files", "*")],
		)
		if path:
			self.set_card(path)

	def set_card(self, path):
		"""Open the card at `path`. Unlike typing a path into the file field, its errors are shown immediately."""

		self.vars["card"].set(path)
		self.last_changed = None

	def save(self):
		# make sure the saved document matches the current settings
		self.update_document()
		if self.error:
			self.report_error()
			return
		if not self.document:
			messagebox.showerror("Cannot save", "Nothing to save.", parent=self.root)
			return

		default = default_output_path(self.vars["card"].get())
		path = filedialog.asksaveasfilename(
			parent=self.root,
			title="Save imposed pdf",
			initialdir=os.path.dirname(default),
			initialfile=os.path.basename(default),
			defaultextension=".pdf",
			filetypes=[("PDF files", "*.pdf")],
		)
		if not path:
			return

		try:
			self.document.save(path)
		except (RuntimeError, OSError) as e:
			messagebox.showerror("Cannot save", str(e), parent=self.root)


def main():
	parser = argparse.ArgumentParser(prog="cardimpose-gui", description="Impose cards with a live preview.")
	parser.add_argument("card", metavar="CARD", nargs="?", help="The path of the pdf file containing the card.")
	args = parser.parse_args()

	root = tk.Tk()
	App(root, args.card)
	root.mainloop()


if __name__ == "__main__":
	main()
