import tkinter as tk
import unittest
from unittest import mock

from cardimpose.cardimpose import CardImpose
from cardimpose.gui import App, Settings, add_default_unit, check_settings, default_output_path, impose


class TestImposeSettings(unittest.TestCase):

	def test_defaults_fill_page(self):
		document, rows, cols = impose(Settings(card="tests/card.pdf"))
		self.assertEqual((rows, cols), (5, 2))
		self.assertEqual(document.page_count, 1)

	def test_matches_library(self):
		document, _, _ = impose(Settings(card="tests/card.pdf", gutter="5mm", bleed="3mm"))
		expected = CardImpose("tests/card.pdf").set_gutter("5mm").set_bleed("3mm").fill_page()
		self.assertEqual(document[0].get_drawings(), expected[0].get_drawings())

	def test_fixed_grid(self):
		_, rows, cols = impose(Settings(card="tests/card.pdf", nup="2x1"))
		self.assertEqual((rows, cols), (2, 1))

	def test_crop_marks_disabled(self):
		document, _, _ = impose(Settings(card="tests/card.pdf", crop_marks=False))
		self.assertEqual(document[0].get_drawings(), [])

	def test_invalid_settings(self):
		for settings in [
			Settings(),
			Settings(card="tests/card.pdf", gutter="5"),
			Settings(card="tests/card.pdf", nup="2x"),
			Settings(card="tests/card.pdf", pages="7"),
			Settings(card="tests/does_not_exist.pdf"),
		]:
			with self.subTest(settings=settings):
				with self.assertRaises((ValueError, RuntimeError, OSError)):
					impose(settings)

	def test_add_default_unit(self):
		for value, expected in [
			("5", "5mm"),
			("2.5", "2.5mm"),
			("5mm", "5mm"),
			("0.2in", "0.2in"),
			("10px", "10px"),
			("5x3", "5mmx3mm"),
			("5cmx3", "5cmx3mm"),
			("5 x 3", "5mmx3mm"),
			("", ""),
			("A4", "A4"),
			("Tabloid-Extra", "Tabloid-Extra"),
			("abc", "abc"),
		]:
			with self.subTest(value=value):
				self.assertEqual(add_default_unit(value), expected)

	def test_check_settings(self):
		check_settings(Settings())
		check_settings(Settings(page_size="200mmx300mm", nup="2x3", bleed="3mm"))
		for settings in [
			Settings(page_size="B99"),
			Settings(gutter="abc"),
			Settings(margin="5"),
			Settings(bleed="3"),
			Settings(crop_mark_thickness="x"),
			Settings(nup="2x"),
			Settings(nup="0x2"),
		]:
			with self.subTest(settings=settings):
				with self.assertRaises(ValueError):
					check_settings(settings)

	def test_default_output_path(self):
		self.assertEqual(default_output_path("/a/card.pdf"), "/a/card_imposed.pdf")


class TestApp(unittest.TestCase):

	def setUp(self):
		try:
			self.root = tk.Tk()
		except tk.TclError:
			self.skipTest("no display available")
		self.root.withdraw()
		self.app = App(self.root, "tests/card.pdf")

	def tearDown(self):
		self.root.destroy()

	def widget(self, name):
		"""The text field of the setting `name`."""
		return next(widget for widget, n in self.app.text_inputs.items() if n == name)

	def leave(self, name):
		"""Simulate the user leaving the text field of the setting `name`."""
		self.app._on_input_done(self.widget(name))

	def test_update(self):
		self.app.update_document()
		self.assertIsNone(self.app.error)
		self.assertEqual(self.app.grid_size, (5, 2))

	def test_invalid_input_keeps_last_document(self):
		self.app.update_document()
		document = self.app.document
		self.app.vars["margin"].set("abc")
		self.app.update_document()
		self.assertIsNotNone(self.app.error)
		self.assertIs(self.app.document, document)

	def test_numbers_without_unit_are_mm(self):
		self.app.vars["margin"].set("15")
		self.app.update_document()
		self.assertIsNone(self.app.error)
		self.assertEqual(self.app.settings().margin, "15mm")

	def test_leaving_a_field_adds_the_unit(self):
		self.app.vars["gutter"].set("5x2")
		self.leave("gutter")
		self.assertEqual(self.app.vars["gutter"].get(), "5mmx2mm")

	def test_emptied_field_is_reset_to_last_valid_value(self):
		self.app.vars["margin"].set("15mm")
		self.app.update_document()
		self.app.vars["margin"].set("abc")
		self.app.update_document()
		# while the field is empty, the last valid value is used
		self.app.vars["margin"].set("")
		self.assertEqual(self.app.settings().margin, "15mm")
		self.app.update_document()
		self.assertIsNone(self.app.error)
		# and is put back into the field when leaving it
		self.leave("margin")
		self.assertEqual(self.app.vars["margin"].get(), "15mm")

	def test_emptied_fields_before_first_update_use_defaults(self):
		for name in ["page_size", "rows"]:
			self.app.vars[name].set(" ")
			self.leave(name)
		self.assertEqual(self.app.vars["page_size"].get(), Settings.page_size)
		self.assertEqual(self.app.vars["rows"].get(), "2")

	def test_optional_fields_stay_empty(self):
		self.app.vars["bleed"].set("3mm")
		self.app.update_document()
		self.app.vars["bleed"].set("")
		self.leave("bleed")
		self.assertEqual(self.app.vars["bleed"].get(), "")
		self.assertEqual(self.app.settings().bleed, "")

	@mock.patch("cardimpose.gui.messagebox.showerror")
	def test_invalid_field_keeps_the_focus(self, showerror):
		self.app.update_document()
		self.app.vars["margin"].set("abc")
		# no message box while typing
		self.app._scheduled_update()
		showerror.assert_not_called()

		# the message box is shown every time the field is left, and the field gets the focus back
		with mock.patch.object(self.widget("margin"), "focus_set") as focus_set:
			for count in (1, 2, 3):
				self.leave("margin")
				self.assertEqual(showerror.call_count, count)
				self.assertEqual(focus_set.call_count, count)

		# leaving other fields does not show the error of the margin
		self.leave("gutter")
		self.assertEqual(showerror.call_count, 3)

		# until the field is fixed
		self.app.vars["margin"].set("10mm")
		self.leave("margin")
		self.assertIsNone(self.app.error)
		self.assertEqual(showerror.call_count, 3)

	@mock.patch("cardimpose.gui.messagebox.showerror")
	def test_errors_of_other_changes_are_shown_immediately(self, showerror):
		self.app.update_document()
		# the card has a single page, which can not alternate with a backside
		self.app.vars["backside"].set("alternating")
		self.app._scheduled_update()
		self.assertEqual(showerror.call_count, 1)
		# no text field caused the error, so leaving one does not show it again
		self.assertEqual(self.app.error_source, "backside")
		self.leave("margin")
		self.assertEqual(showerror.call_count, 1)

	@mock.patch("cardimpose.gui.messagebox.showerror")
	def test_fields_can_be_changed_before_opening_a_card(self, showerror):
		self.root.destroy()
		self.root = tk.Tk()
		self.root.withdraw()
		self.app = App(self.root)

		for name, value in [("margin", "12"), ("gutter", "2"), ("page_size", "220x300"), ("crop_mark_length", "4")]:
			self.app.vars[name].set(value)
			self.leave(name)
		showerror.assert_not_called()
		self.assertIsNone(self.app.error)
		self.assertIsNone(self.app.document)

		# invalid values are still reported
		self.app.vars["margin"].set("abc")
		self.leave("margin")
		self.assertEqual(showerror.call_count, 1)
		self.app.vars["margin"].set("")
		self.leave("margin")
		self.assertEqual(self.app.vars["margin"].get(), "12mm")
		self.assertEqual(showerror.call_count, 1)

		# opening a card afterwards uses the settings
		self.app.set_card("tests/card.pdf")
		self.app._scheduled_update()
		self.assertIsNone(self.app.error)
		self.assertIsNotNone(self.app.document)

	@mock.patch("cardimpose.gui.messagebox.showerror")
	def test_message_box_does_not_trigger_itself(self, showerror):
		self.app.vars["margin"].set("abc")
		self.leave("margin")
		# the message box takes the focus from the field while it is open
		showerror.side_effect = lambda *_, **__: self.app._on_input_left(self.widget("margin"))
		self.leave("margin")
		self.assertEqual(showerror.call_count, 2)

	def test_fixed_grid_starts_from_current_grid(self):
		self.app.update_document()
		self.app.vars["grid"].set("fixed")
		self.assertEqual(self.app.settings().nup, "5x2")

	def test_page_navigation(self):
		self.app.vars["pages"].set("1,1")
		self.app.update_document()
		self.assertEqual(self.app.document.page_count, 2)
		self.app.show_page(1)
		self.assertEqual(self.app.page_index, 1)
		self.app.show_page(5)
		self.assertEqual(self.app.page_index, 1)
