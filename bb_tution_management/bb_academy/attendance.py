import frappe
from frappe.utils import getdate, now, today, add_days, get_first_day, get_last_day
import json

@frappe.whitelist()
def get_server_today():
    """Today's date in the site's timezone.

    The PWA runs on phones, whose timezone/clock need not match the site's.
    Deriving "today" from the device let it send a date the server considers
    to be in the future, which save_student_attendance rejects outright.
    """
    return today()


@frappe.whitelist()
def get_attendance_students(standard, batch, attendance_date, gender=None):
    if not frappe.has_permission("Student Attendance", "read"):
        frappe.throw("No permission to read attendance")

    date_obj = getdate(attendance_date)

    # 1. Check for Holiday. A Special Class Day cancels it for this scope, in
    #    which case the day lists students exactly like an ordinary one.
    day = get_day_context(date_obj, standard, batch)
    holiday = day["holiday"]
    if holiday:
        return {
            "holiday": holiday,
            "special_class": None,
            "students": [],
            "summary": {},
            "previous_day_pending": None,
        }

    # 2. Get active students for the standard and batch, filtering by admission_date
    gender_filter = " AND gender = %s" if gender else ""
    params = [standard, batch, batch, date_obj]
    if gender:
        params.append(gender)

    students = frappe.db.sql("""
        SELECT name, student_name, admission_date, gender, date_of_birth, image, attendance_batch_set, current_batch
        FROM `tabStudent`
        WHERE status = 'Active'
          AND standard = %s
          AND (
              (IFNULL(attendance_batch_set, 0) = 1 AND attendance_batch = %s)
              OR (IFNULL(attendance_batch_set, 0) = 0 AND current_batch = %s)
          )
          AND admission_date <= %s
          {gender_filter}
        ORDER BY TRIM(SUBSTRING_INDEX(student_name, '.', -1)) ASC
    """.format(gender_filter=gender_filter), tuple(params), as_dict=True)
    
    student_ids = [s.name for s in students]
    if not student_ids:
        return {
            "students": [],
            "summary": {
                "present": 0, "absent": 0, "late": 0, "pending": 0, "holiday": 0,
                "second_present": 0, "second_absent": 0, "second_late": 0, "second_pending": 0,
                "first_round_complete": False,
            },
            "holiday": None,
            "special_class": day["special_class"],
            "previous_day_pending": None,
        }
        
    # 3. Get Today's attendance
    today_att = frappe.db.sql("""
        SELECT student, status, second_time_attendance_status
        FROM `tabStudent Attendance`
        WHERE attendance_date = %s
          AND student IN %s
    """, (date_obj, tuple(student_ids)), as_dict=True)
    today_map = {r.student: r.status for r in today_att}
    second_map = {r.student: r.second_time_attendance_status for r in today_att}
    
    # 4. Get Previous working day's attendance
    # Find the last attendance date before this date for any of these students
    prev_date = frappe.db.sql("""
        SELECT MAX(attendance_date) as dt
        FROM `tabStudent Attendance`
        WHERE attendance_date < %s
          AND student IN %s
    """, (date_obj, tuple(student_ids)))
    
    prev_map = {}
    if prev_date and prev_date[0][0]:
        prev_att = frappe.db.sql("""
            SELECT student, status
            FROM `tabStudent Attendance`
            WHERE attendance_date = %s
              AND student IN %s
        """, (prev_date[0][0], tuple(student_ids)), as_dict=True)
        prev_map = {r.student: r.status for r in prev_att}
        
    # 5. Get Monthly Stats
    first_day = get_first_day(date_obj)
    last_day = get_last_day(date_obj)
    monthly_att = frappe.db.sql("""
        SELECT student, status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %s AND %s
          AND student IN %s
          AND status IN ('Absent', 'Late')
        GROUP BY student, status
    """, (first_day, last_day, tuple(student_ids)), as_dict=True)
    
    monthly_map = {s: {"Absent": 0, "Late": 0} for s in student_ids}
    for row in monthly_att:
        monthly_map[row.student][row.status] = row.cnt
        
    # 6. Get Late Permissions
    late_permissions = frappe.db.sql("""
        SELECT student, late_reason, parents_informed
        FROM `tabLate Permission`
        WHERE date = %s AND student IN %s
    """, (date_obj, tuple(student_ids)), as_dict=True)
    lp_map = {p.student: p for p in late_permissions}

    # 7. Student-wise holidays covering this date
    sh_map = get_student_holidays(student_ids, date_obj)

    # Combine data
    result_students = []
    summary = {
        "present": 0, "absent": 0, "late": 0, "pending": 0, "holiday": 0,
        "second_present": 0, "second_absent": 0, "second_late": 0, "second_pending": 0,
    }
    
    for s in students:
        t_stat = today_map.get(s.name)
        student_holiday = sh_map.get(s.name)
        if student_holiday:
            # Off for the day: neither marked nor pending, in either round.
            summary["holiday"] += 1
        elif t_stat == 'Present': summary["present"] += 1
        elif t_stat == 'Absent': summary["absent"] += 1
        elif t_stat == 'Late': summary["late"] += 1
        else: summary["pending"] += 1

        # Second round is only ever recorded on a row the first round created,
        # so an unmarked first round counts as pending here too.
        s_stat = second_map.get(s.name)
        if student_holiday: pass
        elif s_stat == 'Present': summary["second_present"] += 1
        elif s_stat == 'Absent': summary["second_absent"] += 1
        elif s_stat == 'Late': summary["second_late"] += 1
        else: summary["second_pending"] += 1
        
        # Calculate if new joiner (joined within 7 days of attendance date)
        is_new_joiner = False
        if s.admission_date:
            days_diff = (date_obj - s.admission_date).days
            if 0 <= days_diff <= 7:
                is_new_joiner = True
                
        is_birthday = False
        if s.date_of_birth:
            if s.date_of_birth.month == date_obj.month and s.date_of_birth.day == date_obj.day:
                is_birthday = True

        lp = lp_map.get(s.name)

        is_temporary = False
        if s.attendance_batch_set == 1 and s.current_batch != batch:
            is_temporary = True

        result_students.append({
            "student_id": s.name,
            "student_name": s.student_name,
            "gender": s.gender,
            "today_status": t_stat,
            "previous_status": prev_map.get(s.name, "N/A"),
            "monthly_absent": monthly_map[s.name]["Absent"],
            "monthly_late": monthly_map[s.name]["Late"],
            "is_new_joiner": is_new_joiner,
            "is_birthday": is_birthday,
            "image": s.image or "",
            "has_late_permission": 1 if lp else 0,
            "late_reason": lp.late_reason if lp else "",
            "parents_informed": lp.parents_informed if lp else 0,
            "is_temporary": is_temporary,
            "original_batch": s.current_batch,
            "second_status": second_map.get(s.name),
            "student_holiday": student_holiday,
        })

    # Gates the "Second Attendance" toggle in both UIs: the second round can
    # only start once every listed student has a first-round status, because
    # it writes onto the row the first round created.
    summary["first_round_complete"] = bool(students) and summary["pending"] == 0

    # Blocks marking in the UI until the last open working day is closed off.
    # Computed here rather than in a second round-trip so the screen never
    # renders a markable table it is about to lock.
    return {
        "students": result_students,
        "summary": summary,
        "holiday": None,
        "special_class": day["special_class"],
        "previous_day_pending": _previous_day_pending(standard, batch, date_obj),
    }


# ---------------------------------------------------------------------------
# Previous working day guard
# ---------------------------------------------------------------------------

# How far back the guard will walk past consecutive holidays looking for the
# last working day. Beyond this the batch is treated as clear rather than
# scanning an unbounded stretch of the calendar.
PREV_DAY_LOOKBACK_DAYS = 30


def _get_batch_students(standard, batch, date_obj):
    """Active students of this standard+batch as of `date_obj`.

    Deliberately ignores the screen's gender filter: completeness of a day is a
    property of the whole batch, not of whichever slice is on screen.
    """
    return frappe.db.sql("""
        SELECT name, student_name
        FROM `tabStudent`
        WHERE status = 'Active'
          AND standard = %s
          AND (
              (IFNULL(attendance_batch_set, 0) = 1 AND attendance_batch = %s)
              OR (IFNULL(attendance_batch_set, 0) = 0 AND current_batch = %s)
          )
          AND admission_date <= %s
        ORDER BY TRIM(SUBSTRING_INDEX(student_name, '.', -1)) ASC
    """, (standard, batch, batch, date_obj), as_dict=True)


def _previous_day_pending(standard, batch, attendance_date):
    """Details of the last working day before `attendance_date` that is still
    unfinished, or None when the batch is clear to mark `attendance_date`.

    A day counts as finished when it is a holiday for this standard/batch, or
    when every student active on that day carries a first-round status. Holidays
    are skipped over so a Monday is validated against the previous Saturday.

    Returns None (rather than blocking) in the cases where there is nothing to
    complete: the batch has no students, or it has never had attendance taken
    at all — otherwise a newly onboarded batch could never record its first day.
    """
    date_obj = getdate(attendance_date)

    students = _get_batch_students(standard, batch, date_obj)
    if not students:
        return None

    student_ids = tuple(s.name for s in students)
    started_on = frappe.db.sql("""
        SELECT MIN(attendance_date)
        FROM `tabStudent Attendance`
        WHERE student IN %s
    """, (student_ids,))[0][0]
    if not started_on:
        return None

    started_on = getdate(started_on)
    cursor = getdate(add_days(date_obj, -1))

    for _ in range(PREV_DAY_LOOKBACK_DAYS):
        if cursor < started_on:
            # Nothing was ever recorded on or before this day for this batch,
            # so there is no earlier day left to complete.
            return None

        if get_holiday_details(cursor, standard, batch):
            cursor = getdate(add_days(cursor, -1))
            continue

        day_students = _get_batch_students(standard, batch, cursor)
        if not day_students:
            # No student had joined yet on that day.
            return None

        # Students on a student-wise holiday that day owe no attendance.
        off = get_student_holidays([s.name for s in day_students], cursor)
        day_students = [s for s in day_students if s.name not in off]
        if not day_students:
            return None

        day_ids = tuple(s.name for s in day_students)
        marked = {
            r[0] for r in frappe.db.sql("""
                SELECT student
                FROM `tabStudent Attendance`
                WHERE attendance_date = %s
                  AND student IN %s
                  AND IFNULL(status, '') != ''
            """, (cursor, day_ids))
        }

        pending = [s for s in day_students if s.name not in marked]
        if not pending:
            return None

        return {
            "date": str(cursor),
            "standard": standard,
            "batch": batch,
            "total": len(day_students),
            "marked": len(day_students) - len(pending),
            "pending_count": len(pending),
            "students": [
                {"student_id": s.name, "student_name": s.student_name}
                for s in pending
            ],
        }

    return None


@frappe.whitelist()
def get_previous_day_status(standard, batch, attendance_date):
    """Whitelisted view of the guard, for a UI that wants to re-check on demand."""
    if not frappe.has_permission("Student Attendance", "read"):
        frappe.throw("No permission to read attendance")

    return {"pending": _previous_day_pending(standard, batch, attendance_date)}


def _guard_previous_day(standard, batch, attendance_date):
    """Refuse to record `attendance_date` while an earlier working day is open.

    Enforced here and not only in the UI: the desk page, a stale browser tab and
    a direct API call all reach these endpoints too.
    """
    pending = _previous_day_pending(standard, batch, attendance_date)
    if not pending:
        return

    frappe.throw(
        "Previous day attendance is still pending for {date} — {pending} of {total} "
        "students are unmarked for Standard {standard} / Batch {batch}. "
        "Complete {date} for this standard and batch (or mark it a holiday) "
        "before taking attendance for {today}.".format(
            date=pending["date"],
            pending=pending["pending_count"],
            total=pending["total"],
            standard=standard,
            batch=batch,
            today=getdate(attendance_date),
        ),
        title="Previous Day Attendance Pending",
    )


def _validate_status(status, fieldname="status"):
    """Check `status` against the doctype's Select options.

    The update path below writes with raw SQL, which bypasses Frappe's
    _validate_selects(). Without this, an unknown status (e.g. "Vacation")
    was silently written whenever the row already existed.
    """
    options = frappe.get_meta("Student Attendance").get_field(fieldname).options or ""
    allowed = [o.strip() for o in options.split("\n") if o.strip()]
    if status not in allowed:
        frappe.throw(
            f"Invalid attendance status: {status}. Must be one of {', '.join(allowed)}.",
            title="Invalid Status",
        )


def _update_attendance_row(student, attendance_date, status, late_reason=None):
    """UPDATE the single row for this student+date. Returns True if one matched.

    Deliberately a raw UPDATE rather than get_doc().save():

    * Two concurrent saves of the same document trip Frappe's optimistic lock
      (TimestampMismatchError), which is what a double-tap produces.
    * InnoDB runs at REPEATABLE READ, so a plain SELECT in this transaction
      cannot see a row another transaction committed after our snapshot began.
      An UPDATE performs a "current read" and always sees the latest row.

    Safe for this doctype specifically: Student Attendance has no doc_events,
    and its only controller hook is `before_insert`, which an UPDATE is not
    meant to run. `modified` always changes, so a matched row is always
    reported as affected.
    """
    values = {
        "status": status,
        "student": student,
        "attendance_date": attendance_date,
        "modified": now(),
        "modified_by": frappe.session.user,
    }
    remarks_set = ""
    if status == "Late" and late_reason:
        remarks_set = ", remarks = %(remarks)s"
        values["remarks"] = late_reason

    frappe.db.sql(
        f"""
        UPDATE `tabStudent Attendance`
        SET status = %(status)s{remarks_set},
            modified = %(modified)s,
            modified_by = %(modified_by)s
        WHERE student = %(student)s AND attendance_date = %(attendance_date)s
        """,
        values,
    )
    return bool(frappe.db._cursor.rowcount)


def _save_second_attendance(student, attendance_date, status):
    """Record the second round onto the row the first round already created.

    Never inserts: the second round is a second reading of the *same* day, so
    it lives in second_time_attendance_status on that one row. A missing row
    means the first round was never taken, which the UI gates against but a
    stale tab or a direct API call can still reach — so it is rejected here
    rather than silently creating a row with no first-round status.
    """
    _validate_status(status, "second_time_attendance_status")

    values = {
        "status": status,
        "student": student,
        "attendance_date": attendance_date,
        "modified": now(),
        "modified_by": frappe.session.user,
    }
    frappe.db.sql(
        """
        UPDATE `tabStudent Attendance`
        SET second_time_attendance_status = %(status)s,
            second_time_attendance_date = %(attendance_date)s,
            modified = %(modified)s,
            modified_by = %(modified_by)s
        WHERE student = %(student)s AND attendance_date = %(attendance_date)s
        """,
        values,
    )
    if not frappe.db._cursor.rowcount:
        frappe.throw(
            f"First attendance is not marked for {student} on {attendance_date}. "
            "Complete the first attendance before taking the second one.",
            title="First Attendance Missing",
        )


def _upsert_attendance(student, student_name, standard, attendance_date, status, late_reason=None):
    """Create or update one Student Attendance row, idempotently.

    Student Attendance is named `ATT-{student}-{attendance_date}`, so only one
    row per student per day can exist. "Look it up, else insert" is not safe:
    two requests for the same student interleave between the lookup and the
    insert (a double-tap sends two), and the loser surfaced a raw
    DuplicateEntryError to the user.
    """
    _validate_status(status)

    if _update_attendance_row(student, attendance_date, status, late_reason):
        return

    doc = frappe.get_doc({
        "doctype": "Student Attendance",
        "student": student,
        "student_name": student_name,
        "standard": standard,
        "attendance_date": attendance_date,
        "status": status,
    })
    if status == "Late" and late_reason:
        doc.remarks = late_reason

    save_point = "att_upsert"
    frappe.db.savepoint(save_point)
    try:
        doc.insert()
        return
    except frappe.DuplicateEntryError:
        # Lost the race: undo the failed insert and update the winner's row.
        frappe.db.rollback(save_point=save_point)

    if not _update_attendance_row(student, attendance_date, status, late_reason):
        frappe.throw(
            f"Could not save attendance for {student} on {attendance_date}.",
            title="Attendance Not Saved",
        )


@frappe.whitelist()
def save_student_attendance(student, attendance_date, status, late_reason=None, attendance_round=1):
    if not frappe.has_permission("Student Attendance", "write"):
        frappe.throw("No permission to write attendance")

    attendance_round = int(attendance_round or 1)

    # Prevent future attendance
    if getdate(attendance_date) > getdate(today()):
        frappe.throw("Cannot mark attendance for future dates")

    # Get student info
    stu = frappe.get_doc("Student", student)

    # Check if holiday
    batch = stu.attendance_batch if stu.attendance_batch_set else stu.current_batch
    holiday = get_holiday_details(attendance_date, stu.standard, batch)
    if holiday:
        frappe.throw("Cannot mark attendance on a holiday")

    if get_student_holidays([student], attendance_date):
        frappe.throw(
            f"{stu.student_name} is on holiday on {getdate(attendance_date)}. "
            "Remove the student holiday to mark attendance.",
            title="Student On Holiday",
        )

    # Round one only. The second round is optional and writes onto a row the
    # first round already created, so the day it belongs to was validated when
    # that row was saved — re-checking here would strand an in-progress second
    # pass if an earlier day were reopened in the meantime.
    if attendance_round == 1:
        _guard_previous_day(stu.standard, batch, attendance_date)

    if attendance_round == 2:
        _save_second_attendance(student, attendance_date, status)
    else:
        _upsert_attendance(
            student=student,
            student_name=stu.student_name,
            standard=stu.standard,
            attendance_date=attendance_date,
            status=status,
            late_reason=late_reason,
        )

    # Return updated monthly stats
    date_obj = getdate(attendance_date)
    first_day = get_first_day(date_obj)
    last_day = get_last_day(date_obj)
    monthly_att = frappe.db.sql("""
        SELECT status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %s AND %s
          AND student = %s
          AND status IN ('Absent', 'Late')
        GROUP BY status
    """, (first_day, last_day, student), as_dict=True)
    
    monthly_map = {"Absent": 0, "Late": 0}
    for row in monthly_att:
        monthly_map[row.status] = row.cnt
        
    return {
        "status": "success",
        "monthly_absent": monthly_map["Absent"],
        "monthly_late": monthly_map["Late"]
    }

@frappe.whitelist()
def save_bulk_attendance(students, standard, batch, attendance_date, status, late_reason=None, attendance_round=1):
    if not frappe.has_permission("Student Attendance", "write"):
        frappe.throw("No permission to write attendance")

    attendance_round = int(attendance_round or 1)

    if getdate(attendance_date) > getdate(today()):
        frappe.throw("Cannot mark attendance for future dates")

    if isinstance(students, str):
        students = json.loads(students)

    if not students:
        frappe.throw("No students selected")

    holiday = get_holiday_details(attendance_date, standard, batch)
    if holiday:
        frappe.throw("Cannot mark attendance on a holiday")

    # Round one only — see save_student_attendance.
    if attendance_round == 1:
        _guard_previous_day(standard, batch, attendance_date)

    date_obj = getdate(attendance_date)

    # Skipped rather than refused: "select all" on the screen can sweep in a
    # student who is off today, and the rest of the batch should still save.
    on_holiday = get_student_holidays(students, date_obj)
    students = [s for s in students if s not in on_holiday]

    student_names = frappe.db.get_all(
        "Student",
        filters={"name": ["in", students]},
        fields=["name", "student_name"],
    )
    name_map = {s.name: s.student_name for s in student_names}

    count = 0
    for student in students:
        if attendance_round == 2:
            _save_second_attendance(student, attendance_date, status)
        else:
            # Shares the single-row upsert so a bulk save racing an individual one
            # (or another device) updates rather than blowing up on a duplicate key.
            _upsert_attendance(
                student=student,
                student_name=name_map.get(student),
                standard=standard,
                attendance_date=attendance_date,
                status=status,
                late_reason=late_reason,
            )
        count += 1

    return {"status": "success", "count": count, "skipped_on_holiday": sorted(on_holiday)}


@frappe.whitelist()
def get_late_reasons():
    if not frappe.has_permission("Student Attendance", "read"):
        return []

    rows = frappe.db.sql("""
        SELECT remarks, MAX(modified) as last_used
        FROM `tabStudent Attendance`
        WHERE status = 'Late' AND remarks IS NOT NULL AND remarks != ''
        GROUP BY remarks
        ORDER BY last_used DESC
        LIMIT 20
    """, as_dict=True)

    return [r.remarks for r in rows]


@frappe.whitelist()
def get_declared_holiday(attendance_date, standard, batch):
    """The holiday on the register for this date, ignoring whether class ran.

    Use this only to *show* what was declared. Every "can I write to this day"
    check must go through get_holiday_details, which also honours a Special
    Class Day.
    """
    # Entire school
    school_hol = frappe.db.get_value("Attendance Holiday", {"holiday_date": attendance_date, "scope": "Entire School"}, ["holiday_type", "reason"], as_dict=True)
    if school_hol: return school_hol
    
    # Standard
    std_hol = frappe.db.get_value("Attendance Holiday", {"holiday_date": attendance_date, "scope": "Standard", "standard": standard}, ["holiday_type", "reason"], as_dict=True)
    if std_hol: return std_hol
    
    # Standard + Batch
    batch_hol = frappe.db.get_value("Attendance Holiday", {"holiday_date": attendance_date, "scope": "Standard + Batch", "standard": standard, "batch": batch}, ["holiday_type", "reason"], as_dict=True)
    if batch_hol: return batch_hol
    
    return None


@frappe.whitelist()
def get_special_class_day(class_date, standard, batch):
    """The record saying class was conducted on this date despite the holiday.

    Matched the same way holidays are: a school-wide record covers everyone, a
    Standard record covers that standard's batches, and the narrowest covers
    one batch. A school-wide special class therefore lifts a standard-only
    holiday, and a single batch can work through a school-wide holiday.
    """
    for filters in (
        {"class_date": class_date, "scope": "Entire School"},
        {"class_date": class_date, "scope": "Standard", "standard": standard},
        {"class_date": class_date, "scope": "Standard + Batch", "standard": standard, "batch": batch},
    ):
        row = frappe.db.get_value(
            "Special Class Day", filters, ["name", "scope", "reason"], as_dict=True
        )
        if row:
            return row

    return None


@frappe.whitelist()
def get_holiday_details(attendance_date, standard, batch):
    """The holiday that *blocks* this date, or None if the day is workable.

    This is the single gate every read and write path already goes through, so
    honouring the Special Class Day here is what makes a holiday on which class
    was actually taken behave like an ordinary working day everywhere at once —
    the attendance screen, the performance screen, the previous-day guard and
    the monthly register.
    """
    holiday = get_declared_holiday(attendance_date, standard, batch)
    if not holiday:
        return None

    if get_special_class_day(attendance_date, standard, batch):
        return None

    return holiday


@frappe.whitelist()
def get_day_context(date, standard, batch):
    """What the screens need to explain a date: what was declared, whether a
    class was recorded against it anyway, and whether writes are blocked."""
    declared = get_declared_holiday(date, standard, batch)
    special = get_special_class_day(date, standard, batch) if declared else None

    return {
        "declared_holiday": declared,
        "special_class": special,
        "holiday": None if special else declared,
    }

@frappe.whitelist()
def assign_holiday(date, holiday_type, reason, scope, standard=None, batch=None):
    if not frappe.has_permission("Attendance Holiday", "create"):
        frappe.throw("No permission to create holiday")
        
    doc = frappe.get_doc({
        "doctype": "Attendance Holiday",
        "holiday_date": date,
        "holiday_type": holiday_type,
        "reason": reason,
        "scope": scope,
        "standard": standard,
        "batch": batch
    })
    doc.insert()
    return doc.name

@frappe.whitelist()
def assign_special_class_day(date, reason, scope="Standard + Batch", standard=None, batch=None):
    """Record that class was taken on a declared holiday, unblocking the day.

    Defaults to the narrowest scope: one batch working through a holiday must
    not quietly re-open the day for the whole school.
    """
    if not frappe.has_permission("Special Class Day", "create"):
        frappe.throw("No permission to record a class on a holiday")

    date_obj = getdate(date)

    if not get_declared_holiday(date_obj, standard, batch):
        frappe.throw(
            f"{date_obj} is not a holiday for this selection — attendance and performance "
            "can already be recorded.",
            title="Not A Holiday",
        )

    existing = get_special_class_day(date_obj, standard, batch)
    if existing:
        return frappe.get_doc("Special Class Day", existing.name).as_dict()

    doc = frappe.get_doc({
        "doctype": "Special Class Day",
        "class_date": date_obj,
        "scope": scope,
        "standard": standard,
        "batch": batch,
        "reason": reason,
    })
    doc.insert()

    return doc.as_dict()


@frappe.whitelist()
def remove_special_class_day(date, standard=None, batch=None):
    """Undo a Special Class Day, putting the holiday back.

    Whatever was already recorded against the day stays — deleting attendance
    or grades someone deliberately entered would lose real work — so the day
    goes back to being a holiday that happens to carry records.
    """
    if not frappe.has_permission("Special Class Day", "delete"):
        frappe.throw("No permission to remove a class from a holiday")

    existing = get_special_class_day(getdate(date), standard, batch)
    if not existing:
        return {"status": "success", "removed": False}

    frappe.delete_doc("Special Class Day", existing.name)
    return {"status": "success", "removed": True, "scope": existing.scope}


# ---------------------------------------------------------------------------
# Student-wise holidays
# ---------------------------------------------------------------------------

def get_student_holidays(student_ids, date):
    """{student: holiday} for the students among `student_ids` who are on a
    Student Holiday on `date`."""
    student_ids = list(student_ids or [])
    if not student_ids:
        return {}

    rows = frappe.db.sql("""
        SELECT name, student, from_date, to_date, reason
        FROM `tabStudent Holiday`
        WHERE student IN %s
          AND from_date <= %s
          AND to_date >= %s
    """, (tuple(student_ids), getdate(date), getdate(date)), as_dict=True)

    return {r.student: r for r in rows}


@frappe.whitelist()
def assign_student_holiday(students, from_date, to_date, reason):
    """Give the selected students a holiday from `from_date` to `to_date`.

    Attendance already marked for them inside the range is cleared: the day is
    a holiday for them, so an Absent recorded before the holiday was entered
    must not keep counting against the student.
    """
    if not frappe.has_permission("Student Holiday", "create"):
        frappe.throw("No permission to assign a student holiday")

    if isinstance(students, str):
        students = json.loads(students)
    if not students:
        frappe.throw("No students selected")

    reason = (reason or "").strip()
    if not reason:
        frappe.throw("Reason is required")

    from_date, to_date = getdate(from_date), getdate(to_date)
    if to_date < from_date:
        frappe.throw("To Date cannot be before From Date.")

    created = []
    for student in students:
        doc = frappe.get_doc({
            "doctype": "Student Holiday",
            "student": student,
            "from_date": from_date,
            "to_date": to_date,
            "reason": reason,
        })
        doc.insert()
        created.append(doc.name)

    cleared = frappe.db.sql("""
        SELECT name FROM `tabStudent Attendance`
        WHERE student IN %s AND attendance_date BETWEEN %s AND %s
    """, (tuple(students), from_date, to_date), pluck=True)
    for name in cleared:
        frappe.delete_doc("Student Attendance", name)

    return {"status": "success", "created": created, "cleared_attendance": len(cleared)}


@frappe.whitelist()
def remove_student_holiday(name):
    """Delete a Student Holiday, making its days markable again."""
    if not frappe.has_permission("Student Holiday", "delete"):
        frappe.throw("No permission to remove a student holiday")

    frappe.delete_doc("Student Holiday", name)
    return {"status": "success"}


@frappe.whitelist()
def get_attendance_dashboard():
    td = getdate(today())
    sevendays_ago = add_days(td, -6)
    
    new_students = frappe.db.count("Student", {"admission_date": ["between", [sevendays_ago, td]], "status": "Active"})
    today_absent = frappe.db.count("Student Attendance", {"attendance_date": td, "status": "Absent"})
    
    # Absent > 5 Days in current month or academic year?
    # Requirement: "Prefer current academic year or current academic year-to-date. Make this configurable if possible."
    # Let's use current month to make it simple and performant
    first_day = get_first_day(td)
    last_day = get_last_day(td)
    
    absent_5_plus = frappe.db.sql("""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %s AND %s AND status = 'Absent'
            GROUP BY student HAVING count(name) >= 5
        ) AS t
    """, (first_day, last_day))[0][0]
    
    late_5_plus = frappe.db.sql("""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %s AND %s AND status = 'Late'
            GROUP BY student HAVING count(name) >= 5
        ) AS t
    """, (first_day, last_day))[0][0]
    
    # Today summary
    summary_raw = frappe.db.sql("""
        SELECT status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date = %s
        GROUP BY status
    """, (td,), as_dict=True)
    
    summary = {"present": 0, "absent": 0, "late": 0, "pending": 0}
    for row in summary_raw:
        if row.status == "Present": summary["present"] = row.cnt
        elif row.status == "Absent": summary["absent"] = row.cnt
        elif row.status == "Late": summary["late"] = row.cnt
        
    total_active = frappe.db.count("Student", {"status": "Active", "admission_date": ["<=", td]})
    summary["pending"] = total_active - (summary["present"] + summary["absent"] + summary["late"])
    
    return {
        "new_students": new_students,
        "today_absent": today_absent,
        "absent_5_plus": absent_5_plus,
        "late_5_plus": late_5_plus,
        "today_summary": summary
    }


@frappe.whitelist()
def get_attendance_dashboard_data(academic_year=None, standard=None, batch=None, date=None):
    if not date:
        date = today()
        
    date_obj = getdate(date)
    first_day_month = get_first_day(date_obj)
    last_day_month = get_last_day(date_obj)
    
    # Base filters
    std_filter = " AND standard = %(standard)s " if standard else ""
    batch_filter = " AND ((IFNULL(attendance_batch_set, 0) = 1 AND attendance_batch = %(batch)s) OR (IFNULL(attendance_batch_set, 0) = 0 AND current_batch = %(batch)s)) " if batch else ""
    
    # 1. New Students
    sevendays_ago = add_days(date_obj, -6)
    new_students_query = f"""
        SELECT COUNT(name) FROM `tabStudent` 
        WHERE status = 'Active' 
        AND admission_date BETWEEN %(sevendays_ago)s AND %(date)s
        {std_filter} {batch_filter}
    """
    new_students = frappe.db.sql(new_students_query, {
        "sevendays_ago": sevendays_ago, "date": date, "standard": standard, "batch": batch
    })[0][0]
    
    # 2. Today's Absent
    att_std_filter = " AND standard = %(standard)s " if standard else ""
    att_batch_filter = " AND student IN (SELECT name FROM `tabStudent` WHERE ((IFNULL(attendance_batch_set, 0) = 1 AND attendance_batch = %(batch)s) OR (IFNULL(attendance_batch_set, 0) = 0 AND current_batch = %(batch)s))) " if batch else ""
    today_absent_query = f"""
        SELECT COUNT(name) FROM `tabStudent Attendance`
        WHERE attendance_date = %(date)s AND status = 'Absent'
        {att_std_filter} {att_batch_filter}
    """
    today_absent = frappe.db.sql(today_absent_query, {
        "date": date, "standard": standard, "batch": batch
    })[0][0]
    
    # 3. Absent 5+ and Late 5+ (This month)
    abs_5_query = f"""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Absent'
            {att_std_filter} {att_batch_filter}
            GROUP BY student HAVING count(name) >= 5
        ) AS t
    """
    absent_5_plus = frappe.db.sql(abs_5_query, {
        "first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch
    })[0][0]
    
    late_5_query = f"""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Late'
            {att_std_filter} {att_batch_filter}
            GROUP BY student HAVING count(name) >= 5
        ) AS t
    """
    late_5_plus = frappe.db.sql(late_5_query, {
        "first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch
    })[0][0]

    # 4. Absent 10+ and Late 10+ (This month)
    # The dashboard has always rendered these two cards, but the keys were never
    # returned here — so they displayed "undefined".
    abs_10_query = f"""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Absent'
            {att_std_filter} {att_batch_filter}
            GROUP BY student HAVING count(name) >= 10
        ) AS t
    """
    absent_10_plus = frappe.db.sql(abs_10_query, {
        "first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch
    })[0][0]

    late_10_query = f"""
        SELECT COUNT(*) FROM (
            SELECT student FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Late'
            {att_std_filter} {att_batch_filter}
            GROUP BY student HAVING count(name) >= 10
        ) AS t
    """
    late_10_plus = frappe.db.sql(late_10_query, {
        "first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch
    })[0][0]

    # Today Summary Distribution
    summary_raw = frappe.db.sql(f"""
        SELECT status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date = %(date)s
        {att_std_filter} {att_batch_filter}
        GROUP BY status
    """, {"date": date, "standard": standard, "batch": batch}, as_dict=True)
    
    today_summary = {"present": 0, "absent": 0, "late": 0, "pending": 0}
    for row in summary_raw:
        if row.status == "Present": today_summary["present"] = row.cnt
        elif row.status == "Absent": today_summary["absent"] = row.cnt
        elif row.status == "Late": today_summary["late"] = row.cnt
        
    total_active = frappe.db.sql(f"""
        SELECT COUNT(name) FROM `tabStudent`
        WHERE status = 'Active' AND admission_date <= %(date)s
        {std_filter} {batch_filter}
    """, {"date": date, "standard": standard, "batch": batch})[0][0]
    
    today_summary["pending"] = total_active - (today_summary["present"] + today_summary["absent"] + today_summary["late"])
    today_summary["total"] = total_active
    
    # Top 10 Absent
    top_absent = frappe.db.sql(f"""
        SELECT student, student_name, count(name) as absent_count
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Absent'
        {att_std_filter} {att_batch_filter}
        GROUP BY student, student_name
        ORDER BY absent_count DESC
        LIMIT 10
    """, {"first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch}, as_dict=True)
    
    # Top 10 Late
    top_late = frappe.db.sql(f"""
        SELECT student, student_name, count(name) as late_count
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s AND status = 'Late'
        {att_std_filter} {att_batch_filter}
        GROUP BY student, student_name
        ORDER BY late_count DESC
        LIMIT 10
    """, {"first_day": first_day_month, "last_day": last_day_month, "standard": standard, "batch": batch}, as_dict=True)

    # Standard Summary (Bar chart)
    # Only if standard filter is empty
    standard_summary = []
    batch_summary = []
    if not standard:
        standard_summary = frappe.db.sql(f"""
            SELECT standard, status, count(name) as cnt
            FROM `tabStudent Attendance`
            WHERE attendance_date BETWEEN %(first_day)s AND %(last_day)s
            GROUP BY standard, status
        """, {"first_day": first_day_month, "last_day": last_day_month}, as_dict=True)
    else:
        batch_summary = frappe.db.sql(f"""
            SELECT IF(IFNULL(s.attendance_batch_set, 0) = 1, s.attendance_batch, s.current_batch) as batch, a.status, count(a.name) as cnt
            FROM `tabStudent Attendance` a
            JOIN `tabStudent` s ON a.student = s.name
            WHERE a.attendance_date BETWEEN %(first_day)s AND %(last_day)s
            {"AND a.standard = %(standard)s" if standard else ""}
            GROUP BY IF(IFNULL(s.attendance_batch_set, 0) = 1, s.attendance_batch, s.current_batch), a.status
        """, {"first_day": first_day_month, "last_day": last_day_month, "standard": standard}, as_dict=True)
        
    # Last 30 Days Trend
    thirty_days_ago = add_days(date_obj, -29)
    trend_raw = frappe.db.sql(f"""
        SELECT attendance_date, status, count(name) as cnt
        FROM `tabStudent Attendance`
        WHERE attendance_date BETWEEN %(thirty_days)s AND %(date)s
        {att_std_filter} {att_batch_filter}
        GROUP BY attendance_date, status
        ORDER BY attendance_date ASC
    """, {"thirty_days": thirty_days_ago, "date": date, "standard": standard, "batch": batch}, as_dict=True)
    
    return {
        "new_students": new_students,
        "today_absent": today_absent,
        "absent_5_plus": absent_5_plus,
        "late_5_plus": late_5_plus,
        "absent_10_plus": absent_10_plus,
        "late_10_plus": late_10_plus,
        "today_summary": today_summary,
        "top_absent": top_absent,
        "top_late": top_late,
        "standard_summary": standard_summary,
        "batch_summary": batch_summary,
        "trend_raw": trend_raw
    }

