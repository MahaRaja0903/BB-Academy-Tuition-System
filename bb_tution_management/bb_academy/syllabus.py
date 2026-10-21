# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

"""What a class covered: one block per subject, each with its lessons and portions.

A single class can cover more than one subject — Maths, then Science. Frappe
cannot nest a child table inside a child table, so the blocks are stored flat on
the Student Performance Session / Tracker row and regrouped on read:

- `subjects` (Subject Item) — the subjects, in the order they were taught;
- `lessons` (Lesson Item) — every lesson; a Lesson already knows its subject;
- `portions` (Portion Item) — every portion, tagged with the subject it was for.

`subject` keeps the first subject, so anything that reads a single subject (the
student profile, older reports) still has one to show.

Everything here speaks in blocks: `{"subject": ..., "lessons": [...], "portions": [...]}`.
"""

import json

import frappe

from bb_tution_management.bb_tution_management.doctype.subject.subject import (
	subjects_for_standard,
)

SUBJECT_PARENTFIELD = "subjects"
LESSON_PARENTFIELD = "lessons"
PORTION_PARENTFIELD = "portions"


def blank_block(subject=None):
	return {"subject": subject or None, "lessons": [], "portions": []}


def _as_list(value):
	"""Accept a JSON string (what frappe-ui sends) or an already-decoded list."""
	if not value:
		return []
	if isinstance(value, str):
		value = json.loads(value)
	if not isinstance(value, (list, tuple)):
		frappe.throw("Expected a list of values.")
	return [str(v).strip() for v in value if v and str(v).strip()]


def parse_syllabus(syllabus=None, subject=None, lessons=None, portions=None):
	"""Normalise what a client sent into a list of blocks.

	`syllabus` is the multi-subject shape. The single `subject` / `lessons` /
	`portions` arguments are what the PWA sent before a class could cover more
	than one subject; they are read as one block so a stale cached client still
	saves. Returns None when nothing was sent at all, which callers treat as
	"leave the row's syllabus alone" — an empty list means "clear it".
	"""
	if syllabus is not None:
		if isinstance(syllabus, str):
			syllabus = json.loads(syllabus) if syllabus.strip() else []
		if not isinstance(syllabus, (list, tuple)):
			frappe.throw("Expected a list of subjects.")

		blocks = []
		for raw in syllabus:
			if not isinstance(raw, dict):
				frappe.throw("Each subject must carry its subject, lessons and portions.")
			blocks.append(
				{
					"subject": (raw.get("subject") or "").strip() or None,
					"lessons": _as_list(raw.get("lessons")),
					"portions": _as_list(raw.get("portions")),
				}
			)
		return [b for b in blocks if b["subject"] or b["lessons"] or b["portions"]]

	if subject is None and lessons is None and portions is None:
		return None

	block = {
		"subject": subject or None,
		"lessons": _as_list(lessons),
		"portions": _as_list(portions),
	}
	return [block] if block["subject"] or block["lessons"] or block["portions"] else []


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------


def validate_subject(subject, standard):
	"""Keep the PWA honest about the Subject master the dropdown is built from."""
	if not subject:
		return

	if not frappe.db.exists("Subject", subject):
		frappe.throw(f"{subject} is not in the Subject master.", title="Unknown Subject")

	if standard and subject not in subjects_for_standard(standard):
		frappe.throw(
			f"{subject} is not offered for {standard}. "
			f"Add {standard} to the subject's Standard Applicable list first.",
			title="Subject Not Offered",
		)


def validate_syllabus(blocks, standard):
	"""Every block names its own subject once, and every lesson belongs to the
	subject of the block it sits in — otherwise a stale pick left over from a
	subject switch would be saved silently under the wrong subject."""
	if not blocks:
		return

	if len(blocks) > 1 and any(not b["subject"] for b in blocks):
		frappe.throw(
			"Pick a Subject for every subject block, or remove the empty one.",
			title="Subject Missing",
		)

	seen_subjects = set()
	for block in blocks:
		subject = block["subject"]
		if subject:
			if subject in seen_subjects:
				frappe.throw(
					f"{subject} is added twice — put all of its lessons in one block.",
					title="Duplicate Subject",
				)
			seen_subjects.add(subject)
			validate_subject(subject, standard)

	_validate_lessons(blocks, standard)

	for block in blocks:
		portions = block["portions"]
		if len(set(portions)) != len(portions):
			frappe.throw(
				f"A portion is picked twice under {block['subject'] or 'the same subject'}.",
				title="Duplicate Portion",
			)
		unknown = [p for p in portions if not frappe.db.exists("Portion", p)]
		if unknown:
			frappe.throw(
				f"{', '.join(unknown)} is not in the Portion master.", title="Unknown Portion"
			)


def _validate_lessons(blocks, standard):
	names = [name for block in blocks for name in block["lessons"]]
	if not names:
		return

	seen = set()
	for name in names:
		if name in seen:
			frappe.throw(f"{name} is picked twice.", title="Duplicate Lesson")
		seen.add(name)

	rows = {
		r.name: r
		for r in frappe.get_all(
			"Lesson",
			filters={"name": ["in", list(seen)]},
			fields=["name", "standard", "subject"],
		)
	}

	for block in blocks:
		for name in block["lessons"]:
			row = rows.get(name)
			if not row:
				frappe.throw(f"{name} is not in the Lesson master.", title="Unknown Lesson")
			if standard and row.standard != standard:
				frappe.throw(f"{name} is not mapped to {standard}.", title="Lesson Not Mapped")
			if block["subject"] and row.subject != block["subject"]:
				frappe.throw(
					f"{name} is not mapped to {block['subject']}.", title="Lesson Not Mapped"
				)


# ---------------------------------------------------------------------------
# write
# ---------------------------------------------------------------------------


def set_syllabus(doc, blocks):
	"""Flatten the blocks onto a Session / Tracker doc."""
	blocks = blocks or []
	doc.subject = blocks[0]["subject"] if blocks else None
	doc.set(SUBJECT_PARENTFIELD, [{"subject": b["subject"]} for b in blocks if b["subject"]])
	doc.set(LESSON_PARENTFIELD, [{"lesson": n} for b in blocks for n in b["lessons"]])
	doc.set(
		PORTION_PARENTFIELD,
		[{"portion": p, "subject": b["subject"]} for b in blocks for p in b["portions"]],
	)


def has_syllabus(doc):
	return bool(
		doc.get("subject")
		or doc.get(SUBJECT_PARENTFIELD)
		or doc.get(LESSON_PARENTFIELD)
		or doc.get(PORTION_PARENTFIELD)
	)


def sync_subjects(doc):
	"""Keep `subject` and `subjects` agreeing on a doc saved from the desk.

	A row written before multi-subject has only `subject`; one edited in the
	desk has `subjects`. Either way, `subject` ends up as the first subject.
	"""
	subjects = [r.subject for r in (doc.get(SUBJECT_PARENTFIELD) or []) if r.subject]
	if subjects:
		doc.subject = subjects[0]
	elif doc.get("subject"):
		doc.append(SUBJECT_PARENTFIELD, {"subject": doc.subject})


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


def _group(subject, subjects, lessons, portions, lesson_subject):
	"""Regroup one row's flat tables into blocks.

	A portion saved before it carried a subject belongs to the first block. A
	lesson on a subject the row does not list (a desk edit, say) still gets a
	block of its own rather than being hidden under the wrong subject.
	"""
	order = [s for s in subjects if s] or ([subject] if subject else [])
	first = order[0] if order else None
	blocks = {s: blank_block(s) for s in order}

	def block(s):
		s = s or first
		if s not in blocks:
			blocks[s] = blank_block(s)
		return blocks[s]

	for name in lessons:
		block(lesson_subject.get(name))["lessons"].append(name)
	for portion, portion_subject in portions:
		block(portion_subject)["portions"].append(portion)

	return list(blocks.values())


def _lesson_subjects(names):
	names = list({n for n in names if n})
	if not names:
		return {}
	return {
		r.name: r.subject
		for r in frappe.get_all("Lesson", filters={"name": ["in", names]}, fields=["name", "subject"])
	}


def doc_syllabus(doc):
	"""The blocks of a loaded Session / Tracker doc."""
	lessons = [r.lesson for r in (doc.get(LESSON_PARENTFIELD) or [])]
	return _group(
		doc.get("subject"),
		[r.subject for r in (doc.get(SUBJECT_PARENTFIELD) or [])],
		lessons,
		[(r.portion, r.get("subject")) for r in (doc.get(PORTION_PARENTFIELD) or [])],
		_lesson_subjects(lessons),
	)


def syllabus_of(doctype, parents):
	"""parent name -> its blocks, for many rows in a handful of queries."""
	parents = [p for p in parents if p]
	if not parents:
		return {}

	params = {"doctype": doctype, "parents": tuple(parents)}

	subject_col = dict(
		frappe.db.sql(
			f"SELECT `name`, `subject` FROM `tab{doctype}` WHERE `name` IN %(parents)s", params
		)
	)

	subjects = {}
	for row in frappe.db.sql(
		"""
		SELECT `parent`, `subject` FROM `tabSubject Item`
		WHERE parenttype = %(doctype)s AND parentfield = 'subjects' AND parent IN %(parents)s
		ORDER BY idx ASC
		""",
		params,
		as_dict=True,
	):
		subjects.setdefault(row.parent, []).append(row.subject)

	lessons, lesson_subject = {}, {}
	for row in frappe.db.sql(
		"""
		SELECT li.`parent`, li.`lesson`, l.`subject`
		FROM `tabLesson Item` li
		LEFT JOIN `tabLesson` l ON l.name = li.lesson
		WHERE li.parenttype = %(doctype)s AND li.parentfield = 'lessons' AND li.parent IN %(parents)s
		ORDER BY li.idx ASC
		""",
		params,
		as_dict=True,
	):
		lessons.setdefault(row.parent, []).append(row.lesson)
		lesson_subject[row.lesson] = row.subject

	# `portion` is a reserved word in MariaDB (application-time periods), so the
	# column has to be quoted even in a plain SELECT.
	portions = {}
	for row in frappe.db.sql(
		"""
		SELECT `parent`, `portion`, `subject` FROM `tabPortion Item`
		WHERE parenttype = %(doctype)s AND parentfield = 'portions' AND parent IN %(parents)s
		ORDER BY idx ASC
		""",
		params,
		as_dict=True,
	):
		portions.setdefault(row.parent, []).append((row.portion, row.subject))

	return {
		parent: _group(
			subject_col.get(parent),
			subjects.get(parent, []),
			lessons.get(parent, []),
			portions.get(parent, []),
			lesson_subject,
		)
		for parent in parents
	}


def lesson_titles(names):
	"""Lesson docname -> the bare lesson title.

	Lesson names carry their subject and standard so they stay unique; the PWA
	shows only the title, which is all the teacher needs in a crowded row.
	"""
	names = list({n for n in names if n})
	if not names:
		return {}
	return {
		r.name: r.lesson_name
		for r in frappe.get_all("Lesson", filters={"name": ["in", names]}, fields=["name", "lesson_name"])
	}


def syllabus_lessons(blocks):
	return [name for block in blocks or [] for name in block["lessons"]]


def syllabus_text(blocks, titles=None):
	""""Maths: Algebra (2M) · Science: Light" — one line for a report or timeline."""
	titles = titles or {}
	parts = []
	for block in blocks or []:
		bits = ", ".join(titles.get(n, n) for n in block["lessons"])
		if block["portions"]:
			bits = " ".join(filter(None, [bits, f"({', '.join(block['portions'])})"]))
		if block["subject"]:
			bits = f"{block['subject']}: {bits}" if bits else block["subject"]
		if bits:
			parts.append(bits)
	return " · ".join(parts)
