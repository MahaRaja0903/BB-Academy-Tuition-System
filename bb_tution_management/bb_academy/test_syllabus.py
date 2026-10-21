# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""Tests for a class covering more than one subject (Maths and Science on one day).

The pure helpers are tested on plain data. The API tests create their own
Subject / Lesson / Portion masters and grade a student who is already marked
Present, so they never create Students or Attendance (attendance sends a
WhatsApp alert). Every test runs inside a savepoint that is rolled back, and
FrappeTestCase rolls the whole class back at the end, so nothing is left behind.

Run with:
	bench --site <site> run-tests --module bb_tution_management.bb_academy.test_syllabus \
		--skip-test-records --skip-before-tests
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, today

from bb_tution_management.bb_academy import performance as perf
from bb_tution_management.bb_academy.attendance import get_holiday_details
from bb_tution_management.bb_academy.performance_config import PRESENT_STATUSES
from bb_tution_management.bb_academy.syllabus import (
	_group,
	doc_syllabus,
	parse_syllabus,
	syllabus_of,
	syllabus_text,
)
from bb_tution_management.patches import performance_multi_subject

CATEGORY = "Study"


def _block(subject, lessons=(), portions=()):
	return {"subject": subject, "lessons": list(lessons), "portions": list(portions)}


class TestSyllabusHelpers(FrappeTestCase):
	"""No database writes — the shape conversions on their own."""

	def test_nothing_sent_is_none(self):
		# None means "leave the row alone"; it must not be confused with "clear it".
		self.assertIsNone(parse_syllabus())
		self.assertEqual(parse_syllabus(syllabus="[]"), [])

	def test_legacy_single_subject_becomes_one_block(self):
		self.assertEqual(
			parse_syllabus(subject="Maths", lessons='["L1"]', portions=["2M"]),
			[_block("Maths", ["L1"], ["2M"])],
		)

	def test_empty_blocks_are_dropped(self):
		sent = json.dumps([_block("Maths", ["L1"]), _block(""), {"subject": " "}])
		self.assertEqual(parse_syllabus(syllabus=sent), [_block("Maths", ["L1"])])

	def test_bad_shape_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			parse_syllabus(syllabus='["Maths"]')
		with self.assertRaises(frappe.ValidationError):
			parse_syllabus(syllabus='{"subject": "Maths"}')

	def test_group_keeps_subject_order_and_tags(self):
		blocks = _group(
			"Maths",
			["Maths", "Science"],
			["Algebra", "Light"],
			[("2M", "Maths"), ("5M", "Science")],
			{"Algebra": "Maths", "Light": "Science"},
		)
		self.assertEqual(blocks, [_block("Maths", ["Algebra"], ["2M"]), _block("Science", ["Light"], ["5M"])])

	def test_group_reads_rows_saved_before_multi_subject(self):
		# Only `subject` set, portions untagged: everything is one block.
		self.assertEqual(
			_group("Maths", [], ["Algebra"], [("2M", None)], {"Algebra": "Maths"}),
			[_block("Maths", ["Algebra"], ["2M"])],
		)

	def test_group_never_hides_a_lesson_under_the_wrong_subject(self):
		blocks = _group("Maths", ["Maths"], ["Light"], [], {"Light": "Science"})
		self.assertEqual(blocks, [_block("Maths"), _block("Science", ["Light"])])

	def test_text(self):
		blocks = [_block("Maths", ["a"], ["2M"]), _block("Science")]
		self.assertEqual(syllabus_text(blocks, {"a": "Algebra"}), "Maths: Algebra (2M) · Science")
		self.assertEqual(syllabus_text([]), "")


class TestMultiSubjectPerformance(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		cls.ctx = cls._find_present_student()
		if not cls.ctx:
			return

		standard = cls.ctx.standard
		tag = frappe.generate_hash(length=6)
		cls.maths = cls._make_subject(f"_Test Maths {tag}", standard)
		cls.science = cls._make_subject(f"_Test Science {tag}", standard)
		# Mapped to another standard only, so it is not offered here.
		other = frappe.db.get_value("Standard", {"name": ["!=", standard]}, "name")
		cls.foreign = cls._make_subject(f"_Test Foreign {tag}", other) if other else None

		cls.algebra = cls._make_lesson("Algebra", cls.maths, standard)
		cls.ratio = cls._make_lesson("Ratio", cls.maths, standard)
		cls.light = cls._make_lesson("Light", cls.science, standard)

		cls.p1 = cls._make_portion(f"_T1M{tag}")
		cls.p2 = cls._make_portion(f"_T2M{tag}")

	def setUp(self):
		if not self.ctx:
			self.skipTest("No Present student on a past working day to grade.")
		frappe.set_user("Administrator")
		frappe.db.savepoint("syllabus_test")

	def tearDown(self):
		frappe.db.rollback(save_point="syllabus_test")

	# -- fixtures ---------------------------------------------------------

	@staticmethod
	def _find_present_student():
		"""A Present student on a past, non-holiday day, with the batch the
		Performance Manager would list them under."""
		rows = frappe.db.sql(
			"""
			SELECT s.name AS student, s.standard, a.attendance_date AS date,
				IF(IFNULL(s.attendance_batch_set, 0) = 1, s.attendance_batch, s.current_batch) AS batch
			FROM `tabStudent Attendance` a
			INNER JOIN `tabStudent` s ON s.name = a.student
			WHERE a.status IN %(present)s AND a.attendance_date <= %(today)s
				AND s.status = 'Active' AND s.admission_date <= a.attendance_date
				AND IFNULL(s.standard, '') != ''
			ORDER BY a.attendance_date DESC
			LIMIT 50
			""",
			{"present": tuple(PRESENT_STATUSES), "today": getdate(today())},
			as_dict=True,
		)
		for row in rows:
			if row.batch and not get_holiday_details(row.date, row.standard, row.batch):
				return row
		return None

	@staticmethod
	def _make_subject(name, standard):
		return (
			frappe.get_doc(
				{
					"doctype": "Subject",
					"subject_name": name,
					"standard_applicable": [{"standard": standard}],
				}
			)
			.insert()
			.name
		)

	@staticmethod
	def _make_lesson(title, subject, standard):
		return (
			frappe.get_doc(
				{"doctype": "Lesson", "lesson_name": title, "subject": subject, "standard": standard}
			)
			.insert()
			.name
		)

	@staticmethod
	def _make_portion(name):
		return frappe.get_doc({"doctype": "Portion", "portion_name": name}).insert().name

	# -- helpers ----------------------------------------------------------

	def two_subjects(self):
		return [
			_block(self.maths, [self.algebra, self.ratio], [self.p1]),
			_block(self.science, [self.light], [self.p2]),
		]

	def save_setup(self, blocks, **kwargs):
		c = self.ctx
		return perf.save_performance_session(
			c.standard, c.batch, CATEGORY, c.date, syllabus=json.dumps(blocks), **kwargs
		)

	def grade(self, **kwargs):
		c = self.ctx
		kwargs.setdefault("result", "Completed")
		return perf.save_student_performance(
			c.student, c.date, CATEGORY, standard=c.standard, batch=c.batch, **kwargs
		)

	def student_row(self):
		c = self.ctx
		res = perf.get_performance_students(c.standard, c.batch, CATEGORY, c.date)
		return res, next(s for s in res["students"] if s["student_id"] == c.student)

	def clear_existing_grade(self):
		"""Start the student ungraded, so the "inherits the setup" paths run."""
		c = self.ctx
		name = frappe.db.get_value(
			"Student Performance Tracker",
			{"student": c.student, "date": c.date, "category": CATEGORY},
			"name",
		)
		if name:
			frappe.delete_doc("Student Performance Tracker", name)

	# -- batch setup ------------------------------------------------------

	def test_setup_round_trips_two_subjects(self):
		blocks = self.two_subjects()
		res = self.save_setup(blocks)
		self.assertEqual(res["session"]["syllabus"], blocks)

		read, _ = self.student_row()
		self.assertEqual(read["session"]["syllabus"], blocks)
		self.assertEqual(read["lesson_titles"][self.light], "Light")

		name = res["session"]["name"]
		self.assertEqual(frappe.db.get_value("Student Performance Session", name, "subject"), self.maths)
		self.assertEqual(
			frappe.get_all(
				"Portion Item",
				{"parent": name, "parenttype": "Student Performance Session"},
				pluck="subject",
				order_by="idx asc",
			),
			[self.maths, self.science],
		)

	def test_setup_saved_again_replaces_the_subjects(self):
		self.save_setup(self.two_subjects())
		res = self.save_setup([_block(self.science, [self.light])])
		self.assertEqual(res["session"]["syllabus"], [_block(self.science, [self.light])])

	def test_old_client_single_subject_still_saves(self):
		c = self.ctx
		res = perf.save_performance_session(
			c.standard,
			c.batch,
			CATEGORY,
			c.date,
			subject=self.maths,
			lessons=json.dumps([self.algebra]),
			portions=json.dumps([self.p1]),
		)
		self.assertEqual(res["session"]["syllabus"], [_block(self.maths, [self.algebra], [self.p1])])

	def test_rejects_the_same_subject_twice(self):
		with self.assertRaisesRegex(frappe.ValidationError, "added twice"):
			self.save_setup([_block(self.maths, [self.algebra]), _block(self.maths, [self.ratio])])

	def test_rejects_a_lesson_under_another_subject(self):
		with self.assertRaisesRegex(frappe.ValidationError, "not mapped to"):
			self.save_setup([_block(self.maths, [self.light])])

	def test_rejects_a_block_without_subject_when_there_are_several(self):
		with self.assertRaisesRegex(frappe.ValidationError, "every subject block"):
			self.save_setup([_block(self.maths), _block("", [], [self.p1])])

	def test_rejects_a_lesson_picked_in_two_blocks(self):
		with self.assertRaisesRegex(frappe.ValidationError, "picked twice"):
			self.save_setup([_block(self.maths, [self.algebra, self.algebra])])

	def test_rejects_unknown_portion(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Portion master"):
			self.save_setup([_block(self.maths, [], ["_No Such Portion_"])])

	def test_rejects_subject_not_offered_for_the_standard(self):
		if not self.foreign:
			self.skipTest("Only one Standard exists.")
		with self.assertRaisesRegex(frappe.ValidationError, "not offered"):
			self.save_setup([_block(self.maths), _block(self.foreign)])

	def test_empty_setup_clears_the_subjects(self):
		self.save_setup(self.two_subjects())
		res = self.save_setup([])
		self.assertEqual(res["session"]["syllabus"], [])

	# -- per student ------------------------------------------------------

	def test_grade_inherits_the_batch_subjects(self):
		self.clear_existing_grade()
		self.save_setup(self.two_subjects())
		res = self.grade()
		self.assertEqual(res["syllabus"], self.two_subjects())

		_, row = self.student_row()
		self.assertEqual(row["syllabus"], self.two_subjects())

	def test_apply_to_all_restamps_graded_students(self):
		self.save_setup([_block(self.maths, [self.algebra])])
		self.grade()
		res = self.save_setup(self.two_subjects(), apply_to_all=1)
		self.assertGreaterEqual(res["updated_students"], 1)

		_, row = self.student_row()
		self.assertEqual(row["syllabus"], self.two_subjects())

	def test_student_override_survives_a_regrade(self):
		self.save_setup(self.two_subjects())
		mine = [_block(self.science, [self.light], [self.p1])]
		self.assertEqual(self.grade(syllabus=json.dumps(mine))["syllabus"], mine)

		# Tapping a different grade sends no syllabus; the override must stay.
		self.assertEqual(self.grade(result="Excellent")["syllabus"], mine)

		# And the batch setup is untouched by the student's override.
		_, row = self.student_row()
		self.assertEqual(row["syllabus"], mine)
		session = perf._get_session(self.ctx.date, self.ctx.standard, self.ctx.batch, CATEGORY)
		self.assertEqual(session["syllabus"], self.two_subjects())

	def test_student_override_rejects_bad_lesson(self):
		with self.assertRaisesRegex(frappe.ValidationError, "not mapped to"):
			self.grade(syllabus=json.dumps([_block(self.science, [self.algebra])]))

	def test_skip_records_what_the_student_did(self):
		self.save_setup(self.two_subjects())
		did = [_block(self.maths, [self.ratio])]
		res = perf.skip_student_performance(
			self.ctx.student,
			self.ctx.date,
			CATEGORY,
			remarks="Unwell, revised Ratio instead",
			syllabus=json.dumps(did),
			standard=self.ctx.standard,
			batch=self.ctx.batch,
		)
		self.assertEqual(res["result"], "Skipped")
		self.assertEqual(res["syllabus"], did)

	def test_student_entry_falls_back_to_the_setup(self):
		self.clear_existing_grade()
		self.save_setup(self.two_subjects())
		entry = perf.get_student_entry(
			self.ctx.student, self.ctx.date, CATEGORY, self.ctx.standard, self.ctx.batch
		)
		self.assertFalse(entry["exists"])
		self.assertEqual(entry["syllabus"], self.two_subjects())

	# -- desk edits and the migration -------------------------------------

	def test_desk_save_keeps_subject_and_subjects_in_step(self):
		self.save_setup(self.two_subjects())
		name = perf._session_name(self.ctx.date, self.ctx.standard, self.ctx.batch, CATEGORY)
		doc = frappe.get_doc("Student Performance Session", name)

		# Reordering Subjects in the desk moves the "first subject" with it.
		doc.set("subjects", [{"subject": self.science}, {"subject": self.maths}])
		doc.save()
		self.assertEqual(doc.subject, self.science)
		self.assertEqual([b["subject"] for b in doc_syllabus(doc)], [self.science, self.maths])

	def test_category_without_syllabus_drops_subjects(self):
		self.clear_existing_grade()
		doc = frappe.get_doc(
			{
				"doctype": "Student Performance Tracker",
				"student": self.ctx.student,
				"date": self.ctx.date,
				"category": "Behaviour",
				"result": "Good",
				"subjects": [{"subject": self.maths}],
			}
		)
		frappe.db.delete(
			"Student Performance Tracker",
			{"student": self.ctx.student, "date": self.ctx.date, "category": "Behaviour"},
		)
		doc.insert()
		self.assertFalse(doc.subject)
		self.assertEqual(doc.subjects, [])

	def test_migration_turns_old_rows_into_one_block(self):
		res = self.save_setup([_block(self.maths, [self.algebra], [self.p1])])
		name = res["session"]["name"]
		# Put the row back the way it was stored before multi-subject.
		frappe.db.delete("Subject Item", {"parent": name})
		frappe.db.set_value("Portion Item", {"parent": name}, "subject", None)

		# The patch's own steps — `execute()` commits, which a test must not do.
		performance_multi_subject._migrate_subjects(
			"Student Performance Session", "tabStudent Performance Session"
		)
		performance_multi_subject._tag_portions(
			"Student Performance Session", "tabStudent Performance Session"
		)

		self.assertEqual(frappe.get_all("Subject Item", {"parent": name}, pluck="subject"), [self.maths])
		self.assertEqual(frappe.get_all("Portion Item", {"parent": name}, pluck="subject"), [self.maths])
		self.assertEqual(
			syllabus_of("Student Performance Session", [name])[name],
			[_block(self.maths, [self.algebra], [self.p1])],
		)

	# -- adding masters from the PWA --------------------------------------

	def test_add_subject_creates_and_maps(self):
		tag = frappe.generate_hash(length=6)
		name = perf.add_subject(f"_Test Physics {tag}", self.ctx.standard)
		self.assertIn(name, perf.get_subjects(self.ctx.standard))
		# Adding it again just returns it.
		self.assertEqual(perf.add_subject(name, self.ctx.standard), name)

	def test_add_subject_maps_an_existing_one_to_this_standard(self):
		if not self.foreign:
			self.skipTest("Only one Standard exists.")
		self.assertNotIn(self.foreign, perf.get_subjects(self.ctx.standard))
		self.assertEqual(perf.add_subject(self.foreign, self.ctx.standard), self.foreign)
		self.assertIn(self.foreign, perf.get_subjects(self.ctx.standard))

	def test_add_subject_needs_permission(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			perf.add_subject("_Test Nope", self.ctx.standard)
