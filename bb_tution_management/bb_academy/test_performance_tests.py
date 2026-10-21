# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""Tests for Test being graded per Subject + Lesson + Portion combination.

A batch can sit several Tests a day, one per combination, and the same
combination cannot be added twice on one day. Uses the fixtures of
test_syllabus (its own masters, a student already marked Present), and rolls
everything back the same way.

Run with:
	bench --site <site> run-tests --module bb_tution_management.bb_academy.test_performance_tests \
		--skip-test-records --skip-before-tests
"""

import json

import frappe

from bb_tution_management.bb_academy import performance as perf
from bb_tution_management.bb_academy.performance_config import CATEGORIES, combination_key
from bb_tution_management.bb_academy.test_syllabus import TestMultiSubjectPerformance, _block

TEST = "Test"


class TestPerformanceTests(TestMultiSubjectPerformance):
	# Only the tests below — the inherited Study tests already run in test_syllabus.
	@classmethod
	def _own(cls):
		return {n for n in vars(cls) if n.startswith("test_")}

	def run(self, result=None):
		if self._testMethodName not in self._own():
			return result
		return super().run(result)

	def setUp(self):
		super().setUp()
		c = self.ctx
		# Start the day with no Tests for this batch, whatever the site holds.
		for name in frappe.get_all(
			"Student Performance Tracker",
			{"date": c.date, "category": TEST, "student": c.student},
			pluck="name",
		):
			frappe.delete_doc("Student Performance Tracker", name)
		for name in frappe.get_all(
			"Student Performance Session",
			{"date": c.date, "standard": c.standard, "batch": c.batch, "category": TEST},
			pluck="name",
		):
			frappe.db.delete("Student Performance Tracker", {"session": name})
			frappe.delete_doc("Student Performance Session", name)

	def add_test(self, block, session_name=None, total_marks=50):
		c = self.ctx
		return perf.save_performance_session(
			c.standard,
			c.batch,
			TEST,
			c.date,
			syllabus=json.dumps([block]),
			total_marks=total_marks,
			session_name=session_name,
		)["session"]

	def mark(self, session_name, marks):
		c = self.ctx
		return perf.save_student_performance(
			c.student,
			c.date,
			TEST,
			marks_obtained=marks,
			standard=c.standard,
			batch=c.batch,
			session_name=session_name,
		)

	def load(self, session_name=None):
		c = self.ctx
		return perf.get_performance_students(c.standard, c.batch, TEST, c.date, session_name=session_name)

	# -- categories --------------------------------------------------------

	def test_subject_tests_are_gone(self):
		self.assertNotIn("Maths Test", CATEGORIES)
		self.assertNotIn("Accounts Test", CATEGORIES)
		self.assertIn("Test", CATEGORIES)
		self.assertIn("H.W", CATEGORIES)

	def test_key_ignores_pick_order(self):
		self.assertEqual(
			combination_key([_block("M", ["L1", "L2"], ["1M", "2M"])]),
			combination_key([_block("M", ["L2", "L1"], ["2M", "1M"])]),
		)
		self.assertNotEqual(
			combination_key([_block("M", ["L1"], ["1M"])]),
			combination_key([_block("M", ["L1"], ["2M"])]),
		)

	# -- several Tests a day ----------------------------------------------

	def test_different_combinations_are_separate_tests(self):
		first = self.add_test(_block(self.maths, [self.algebra], [self.p1]))
		second = self.add_test(_block(self.maths, [self.algebra], [self.p2]))
		third = self.add_test(_block(self.science, [self.light], [self.p1]))
		self.assertEqual(len({first["name"], second["name"], third["name"]}), 3)

		self.mark(first["name"], 50)
		self.mark(second["name"], 10)

		res = self.load(first["name"])
		self.assertEqual([t.name for t in res["tests"]], [first["name"], second["name"], third["name"]])
		row = next(s for s in res["students"] if s["student_id"] == self.ctx.student)
		self.assertEqual(row["result"], "Full Mark")

		row = next(s for s in self.load(second["name"])["students"] if s["student_id"] == self.ctx.student)
		self.assertEqual(row["result"], "Fail")

		row = next(s for s in self.load(third["name"])["students"] if s["student_id"] == self.ctx.student)
		self.assertIsNone(row["result"])

	def test_same_combination_is_refused(self):
		self.add_test(_block(self.maths, [self.algebra, self.ratio], [self.p1]))
		with self.assertRaisesRegex(frappe.ValidationError, "already added"):
			self.add_test(_block(self.maths, [self.ratio, self.algebra], [self.p1]))

	def test_editing_into_an_existing_combination_is_refused(self):
		self.add_test(_block(self.maths, [self.algebra], [self.p1]))
		other = self.add_test(_block(self.maths, [self.ratio], [self.p1]))
		with self.assertRaisesRegex(frappe.ValidationError, "already added"):
			self.add_test(_block(self.maths, [self.algebra], [self.p1]), session_name=other["name"])

	def test_one_subject_per_test(self):
		with self.assertRaisesRegex(frappe.ValidationError, "one subject"):
			perf.save_performance_session(
				self.ctx.standard,
				self.ctx.batch,
				TEST,
				self.ctx.date,
				syllabus=json.dumps(self.two_subjects()),
			)

	def test_subject_is_required(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Subject"):
			self.add_test(_block("", [], [self.p1]))

	def test_grading_needs_a_test(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Add the Test first"):
			self.mark(None, 20)

	def test_row_carries_the_test_combination(self):
		block = _block(self.maths, [self.algebra], [self.p1])
		test = self.add_test(block)
		res = self.mark(test["name"], 30)
		self.assertEqual(res["syllabus"], [block])
		self.assertEqual(res["session"], test["name"])

	def test_editing_the_combination_moves_graded_rows(self):
		test = self.add_test(_block(self.maths, [self.algebra], [self.p1]))
		self.mark(test["name"], 30)
		moved = _block(self.maths, [self.ratio], [self.p2])
		self.add_test(moved, session_name=test["name"])

		row = next(s for s in self.load(test["name"])["students"] if s["student_id"] == self.ctx.student)
		self.assertEqual(row["syllabus"], [moved])

	def test_a_graded_test_cannot_be_removed(self):
		test = self.add_test(_block(self.maths, [self.algebra], [self.p1]))
		self.mark(test["name"], 30)
		with self.assertRaisesRegex(frappe.ValidationError, "already graded"):
			perf.clear_performance_session(
				self.ctx.standard, self.ctx.batch, TEST, self.ctx.date, session_name=test["name"]
			)

	def test_no_test_day_drops_ungraded_tests_and_undoes(self):
		c = self.ctx
		self.add_test(_block(self.maths, [self.algebra], [self.p1]))
		perf.set_no_session(c.standard, c.batch, TEST, c.date, 1, "Exam week")
		res = self.load()
		self.assertEqual(res["tests"], [])
		self.assertTrue(res["session"]["no_session"])

		perf.set_no_session(c.standard, c.batch, TEST, c.date, 0)
		self.assertIsNone(self.load()["session"])

	def test_adding_a_test_cancels_no_test(self):
		c = self.ctx
		perf.set_no_session(c.standard, c.batch, TEST, c.date, 1, "Exam week")
		test = self.add_test(_block(self.maths, [self.algebra], [self.p1]))
		res = self.load(test["name"])
		self.assertFalse(res["session"]["no_session"])
		self.assertEqual(len(res["tests"]), 1)
