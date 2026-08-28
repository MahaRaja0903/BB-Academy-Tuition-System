frappe.pages['attendance-manager'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Attendance Manager',
        single_column: true
    });

    wrapper.attendance_manager = new AttendanceManager(wrapper);
}

class AttendanceManager {
    constructor(wrapper) {
        this.wrapper = $(wrapper).find('.layout-main-section');
        this.page = wrapper.page;
        this.students = [];
        this.summary = {};
        this.selected = new Set();
        // Optional client-side view filter driven by KPI card clicks.
        // One of: null, 'Present', 'Absent', 'Late', 'Pending'
        this.status_filter = null;

        this.setup_ui();
    }

    setup_ui() {
        this.wrapper.html(frappe.render_template("attendance_manager", {}));

        this.$std = this.wrapper.find('#att-standard');
        this.$batch = this.wrapper.find('#att-batch');
        this.$gender = this.wrapper.find('#att-gender');
        this.$date = this.wrapper.find('#att-date');
        this.$search = this.wrapper.find('#att-search');
        this.$tbody = this.wrapper.find('#att-tbody');
        this.$hol_msg = this.wrapper.find('#holiday-message');
        this.$table = this.wrapper.find('#att-table');
        this.$select_all = this.wrapper.find('#att-toolbar-select-all');
        this.$bulk_bar = this.wrapper.find('#att-bulk-bar');
        this.$bulk_count = this.wrapper.find('#bulk-count');
        this.$kpi_grid = this.wrapper.find('#att-kpi-grid');
        this.$filter_chip = this.wrapper.find('#att-filter-chip');
        this.$filter_chip_label = this.wrapper.find('#att-filter-chip-label');


        this.$date.val(frappe.datetime.get_today());

        this.load_standards();
        this.bind_events();
    }

    bind_events() {
        this.$std.on('change', () => {
            this.load_batches(this.$std.val());
            this.clear_students();
        });
        
        this.$batch.on('change', () => {
            this.load_students();
        });

        this.$gender.on('change', () => {
            this.load_students();
        });

        this.$date.on('change', () => {
            this.load_students();
        });

        this.wrapper.find('#btn-prev-day').on('click', () => {
            let d = frappe.datetime.add_days(this.$date.val(), -1);
            this.$date.val(d);
            this.load_students();
        });

        this.wrapper.find('#btn-next-day').on('click', () => {
            let d = frappe.datetime.add_days(this.$date.val(), 1);
            this.$date.val(d);
            this.load_students();
        });

        this.$search.on('input', (e) => {
            this.apply_row_filters();
        });

        this.wrapper.find('#btn-assign-holiday').on('click', () => {
            this.show_holiday_dialog();
        });

        this.wrapper.find('#att-show-completed').on('change', () => {
            if(this.raw_students) {
                this.render_students(this.raw_students, this.summary);
            }
        });


        this.$tbody.on('change', 'input[type=radio]', (e) => {
            let $input = $(e.target);
            let status = $input.val();
            let $tr = $input.closest('tr');
            let student = $tr.data('id');

            if (status === 'Late') {
                let old_status = $tr.attr('data-current-status') || '';
                let lp_reason = $input.attr('data-lp-reason') || '';
                let desc = lp_reason ? `<div style="color: green; font-weight: bold;"><i class="fa fa-info-circle"></i> Parents informed for late reason</div>` : 'Pick a reason for the late entry.';
                
                this.prompt_late_reason(
                    (late_reason) => this.mark_attendance(student, status, $input, late_reason),
                    () => this.revert_status_selection($tr, old_status),
                    { title: 'Mark Late', primary_label: 'Mark Late', default_reason: lp_reason, description: desc }
                );
            } else {
                this.mark_attendance(student, status, $input);
            }
        });

        this.$tbody.on('change', '.att-row-select', (e) => {
            let $cb = $(e.target);
            let student = $cb.data('id');
            if($cb.is(':checked')) {
                this.selected.add(student);
            } else {
                this.selected.delete(student);
            }
            this.update_bulk_bar();
        });

        this.$select_all.on('change', () => {
            let checked = this.$select_all.is(':checked');
            this.wrapper.find('.att-student-row:visible .att-row-select').each((i, el) => {
                let $cb = $(el);
                $cb.prop('checked', checked);
                let student = $cb.data('id');
                if(checked) {
                    this.selected.add(student);
                } else {
                    this.selected.delete(student);
                }
            });
            this.update_bulk_bar();
        });

        this.wrapper.find('#bulk-clear-selection').on('click', () => {
            this.selected.clear();
            this.$tbody.find('.att-row-select').prop('checked', false);
            this.update_bulk_bar();
        });

        this.wrapper.find('#bulk-mark-present').on('click', () => {
            this.bulk_mark_attendance('Present');
        });

        this.wrapper.find('#bulk-mark-absent').on('click', () => {
            this.bulk_mark_attendance('Absent');
        });

        this.wrapper.find('#bulk-mark-late').on('click', () => {
            this.bulk_mark_attendance('Late');
        });

        this.$kpi_grid.on('click', '.att-kpi-card', (e) => {
            let filter = $(e.currentTarget).data('filter');
            this.set_status_filter(filter === 'total' ? null : filter);
        });

        this.wrapper.find('#att-filter-chip-clear').on('click', () => {
            this.set_status_filter(null);
        });

        this.wrapper.find('#birthday-alert').on('click', () => {
            if (!this.raw_students) return;
            let birthday_students = this.raw_students.filter(s => s.is_birthday);
            if (birthday_students.length === 0) return;
            
            let html = '<ul style="margin-bottom: 0; padding-left: 20px;">';
            birthday_students.forEach(s => {
                html += `<li style="margin-bottom: 5px;"><b>${s.student_name}</b> (${s.student_id})</li>`;
            });
            html += '</ul>';
            
            frappe.msgprint({
                title: __('Birthdays Today 🎂'),
                message: html,
                indicator: 'blue'
            });
        });
    }

    set_status_filter(filter_key) {
        const map = { present: 'Present', absent: 'Absent', late: 'Late', pending: 'Pending' };
        let value = filter_key ? (map[filter_key] || null) : null;

        // Clicking the already-active filter toggles it off.
        this.status_filter = (this.status_filter === value) ? null : value;

        this.update_kpi_active_state();

        if (this.raw_students) {
            this.render_students(this.raw_students, this.summary);
        }
    }

    update_kpi_active_state() {
        this.$kpi_grid.find('.att-kpi-card').removeClass('is-active');

        if (!this.status_filter) {
            this.$kpi_grid.find('.att-kpi-total').addClass('is-active');
            this.$filter_chip.hide();
            return;
        }

        let key = this.status_filter.toLowerCase();
        this.$kpi_grid.find(`.att-kpi-${key}`).addClass('is-active');
        this.$filter_chip_label.text(this.status_filter);
        this.$filter_chip.show();
    }

    // Shows a small dialog asking for a Late Reason. The field is a dropdown
    // of reasons used before (pulled from past attendance remarks — no extra
    // doctype needed), but the user can also just type a brand new reason;
    // it's saved as free text either way.
    prompt_late_reason(on_confirm, on_cancel, opts) {
        opts = opts || {};
        this.show_late_reason_dialog(null, on_confirm, on_cancel, opts);
    }

    show_late_reason_dialog(reason_options, on_confirm, on_cancel, opts) {
        let confirmed = false;

        let d = new frappe.ui.Dialog({
            title: opts.title || 'Mark Late',
            fields: [
                {
                    fieldname: 'html_desc',
                    fieldtype: 'HTML',
                    options: opts.description ? `<div style="margin-bottom: 10px;">${opts.description}</div>` : ''
                },
                {
                    fieldname: 'late_reason',
                    fieldtype: 'Link',
                    options: 'Late Entry Reason',
                    label: 'Late Reason',
                    reqd: 1,
                    default: opts.default_reason || ''
                }
            ],
            primary_action_label: opts.primary_label || 'Mark Late',
            primary_action: (values) => {
                let reason = (values.late_reason || '').trim();
                if(!reason) {
                    frappe.msgprint('Please enter a Late Reason');
                    return;
                }
                confirmed = true;
                d.hide();
                on_confirm(reason);
            },
            on_hide: () => {
                if(!confirmed && on_cancel) on_cancel();
            }
        });

        d.show();
    }

    // Resets a row's status buttons back to a given status without saving
    // anything — used when the user cancels the Late Reason dialog.
    revert_status_selection($tr, status) {
        let $group = $tr.find('.att-status-group');
        $group.find('.att-status-btn').removeClass('active');
        $group.find('input[type=radio]').prop('checked', false);

        if(status) {
            let $label = $group.find(`input[value="${status}"]`).closest('label');
            $label.addClass('active');
            $label.find('input[type=radio]').prop('checked', true);
        }
    }

    // Whether a student with the given today_status should be visible
    // under the current "Show Completed" + KPI filter state.
    student_visible_for_status(status) {
        if (this.status_filter === 'Pending') return !status;
        if (this.status_filter) return status === this.status_filter;

        let show_completed = this.wrapper.find('#att-show-completed').is(':checked');
        return show_completed ? true : !status;
    }

    apply_row_filters() {
        let term = this.$search.val().toLowerCase();
        this.wrapper.find('.att-student-row').each(function() {
            let txt = $(this).data('id').toLowerCase() + " " + $(this).data('name');
            if(txt.indexOf(term) > -1) {
                $(this).show();
            } else {
                $(this).hide();
                $(this).find('.att-row-select').prop('checked', false);
            }
        });
        this.update_bulk_bar();
    }

    update_bulk_bar() {
        // Drop selections for students no longer visible/rendered
        let visible_ids = new Set();
        this.wrapper.find('.att-student-row:visible').each((i, el) => {
            visible_ids.add($(el).data('id'));
        });
        [...this.selected].forEach(id => {
            if(!visible_ids.has(id)) this.selected.delete(id);
        });

        let count = this.selected.size;
        this.$bulk_count.text(count);
        this.$bulk_bar.toggle(count > 0);

        let $visible_checkboxes = this.wrapper.find('.att-student-row:visible .att-row-select');
        let $checked = $visible_checkboxes.filter(':checked');
        if($visible_checkboxes.length === 0) {
            this.$select_all.prop('checked', false).prop('indeterminate', false);
        } else if($checked.length === $visible_checkboxes.length) {
            this.$select_all.prop('checked', true).prop('indeterminate', false);
        } else if($checked.length === 0) {
            this.$select_all.prop('checked', false).prop('indeterminate', false);
        } else {
            this.$select_all.prop('checked', false).prop('indeterminate', true);
        }
    }

    load_standards() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Standard',
                fields: ['name'],
                limit_page_length: 0
            },
            callback: (r) => {
                if(r.message) {
                    let html = '<option value="">Select Standard</option>';
                    r.message.forEach(d => {
                        html += `<option value="${d.name}">${d.name}</option>`;
                    });
                    this.$std.html(html);
                }
            }
        });
    }

    load_batches(standard) {
        if(!standard) {
            this.$batch.html('<option value="">Select Batch</option>').prop('disabled', true);
            return;
        }
        
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Batch',
                fields: ['name'],
                
                limit_page_length: 0
            },
            callback: (r) => {
                let html = '<option value="">Select Batch</option>';
                if(r.message) {
                    r.message.forEach(d => {
                        html += `<option value="${d.name}">${d.name}</option>`;
                    });
                }
                this.$batch.html(html).prop('disabled', false);
            }
        });
    }

    clear_students() {
        this.$tbody.html(this.empty_state_html('fa-graduation-cap', 'Select Standard & Batch',
            'Choose a Standard and Batch above to load students and start marking attendance.'));
        this.students = [];
        this.raw_students = null;
        this.status_filter = null;
        this.update_kpi_active_state();
        this.selected.clear();
        this.update_bulk_bar();
        this.update_summary({present: 0, absent: 0, late: 0, pending: 0});
        this.wrapper.find('#sum-total').text(0);
        this.$hol_msg.hide();
        this.$table.show();
    }

    empty_state_html(icon, title, text, extra_class) {
        return `<tr class="att-placeholder-row"><td colspan="5">
            <div class="att-empty-state ${extra_class || ''}">
                <div class="att-empty-icon"><i class="fa ${icon}"></i></div>
                <h4>${frappe.utils.escape_html(title)}</h4>
                <p>${frappe.utils.escape_html(text)}</p>
            </div>
        </td></tr>`;
    }

    render_skeleton() {
        let row = `<tr class="att-skeleton-row"><td colspan="5">
            <div class="att-skeleton-bar" style="width: 40%; margin-bottom: 8px;"></div>
            <div class="att-skeleton-bar" style="width: 70%;"></div>
        </td></tr>`;
        this.$tbody.html(row.repeat(4));
    }

    load_students() {
        let std = this.$std.val();
        let batch = this.$batch.val();
        let gender = this.$gender.val();
        let date = this.$date.val();

        if(!std || !batch || !date) return;

        this.status_filter = null;
        this.update_kpi_active_state();
        this.$hol_msg.hide();
        this.$table.show();
        this.render_skeleton();

        frappe.call({
            method: 'bb_tution_management.bb_academy.attendance.get_attendance_students',
            args: {
                standard: std,
                batch: batch,
                gender: gender,
                attendance_date: date
            },
            freeze: true,
            callback: (r) => {
                if(r.message) {
                    if(r.message.holiday) {
                        this.show_holiday(r.message.holiday);
                    } else {
                        this.raw_students = r.message.students;
                        this.render_students(r.message.students, r.message.summary);
                    }
                }
            }
        });
    }

    show_holiday(hol) {
        this.$table.hide();
        this.$hol_msg.show();
        this.$hol_msg.find('#hol-type').text(hol.holiday_type);
        this.$hol_msg.find('#hol-reason').text(hol.reason);
        this.raw_students = null;
        this.status_filter = null;
        this.update_kpi_active_state();
        this.selected.clear();
        this.update_bulk_bar();
        this.update_summary({present: 0, absent: 0, late: 0, pending: 0});
        this.wrapper.find('#sum-total').text(0);
    }

    render_students(students, summary) {
        this.$hol_msg.hide();
        this.$table.show();
        this.selected.clear();

        let visible_students = students.filter(s => this.student_visible_for_status(s.today_status));
        this.students = visible_students;

        this.update_summary(summary);
        this.wrapper.find('#sum-total').text(students.length);
        this.update_kpi_active_state();

        let birthday_students = students.filter(s => s.is_birthday);
        if (birthday_students.length > 0) {
            this.wrapper.find('#birthday-alert').show();
            this.wrapper.find('#birthday-count-text').text(birthday_students.length);
        } else {
            this.wrapper.find('#birthday-alert').hide();
        }

        if(students.length === 0) {
            this.$tbody.html(this.empty_state_html('fa-graduation-cap', 'No Students Found',
                'No active students found for this Standard and Batch on the selected date.'));
            this.update_bulk_bar();
            return;
        }

        if(visible_students.length === 0) {
            if(this.status_filter) {
                this.$tbody.html(this.empty_state_html('fa-info-circle', `No ${this.status_filter} Students`,
                    `No students match the "${this.status_filter}" filter for this selection.`));
            } else {
                this.$tbody.html(this.empty_state_html('fa-check-circle', 'All Done!',
                    'Awesome! All attendance has been marked for this date.', 'is-success'));
            }
            this.update_bulk_bar();
            return;
        }

        let html = '';
        let template = this.wrapper.find('#att-row-template').html();

        visible_students.forEach(s => {
            let row = template;
            row = row.replace(/\${student_id}/g, s.student_id);
            row = row.replace(/\${student_name}/g, s.student_name);
            row = row.replace(/\${student_name_lower}/g, (s.student_name || "").toLowerCase());
            row = row.replace(/\${today_status_raw}/g, s.today_status || "");
            row = row.replace(/\${monthly_absent}/g, s.monthly_absent);
            row = row.replace(/\${monthly_late}/g, s.monthly_late);
            row = row.replace(/\${previous_status}/g, s.previous_status);
            row = row.replace(/\${new_joiner_class}/g, s.is_new_joiner ? 'att-new-joiner' : '');
            row = row.replace(/\${gender}/g, s.gender || "");
            row = row.replace(/\${gender_icon}/g, s.gender === 'Girls' ? 'fa-female' : (s.gender === 'Boys' ? 'fa-male' : ''));
            row = row.replace(/\${gender_icon_class}/g, s.gender === 'Girls' ? 'att-gender-icon-female' : (s.gender === 'Boys' ? 'att-gender-icon-male' : ''));
            
            let lp_msg = "";
            let lp_disabled = "";
            let lp_disabled_attr = "";
            let lp_reason = "";
            if(s.has_late_permission) {
                lp_msg = `<div style="font-size: 11px; color: #856404; background: #fff3cd; padding: 2px 5px; border-radius: 3px; margin-top: 5px;"><i class="fa fa-info-circle"></i> Parents informed for late reason: ${s.late_reason}</div>`;
                lp_disabled = "disabled";
                lp_disabled_attr = "disabled";
                lp_reason = s.late_reason;
            }
            row = row.replace(/\${lp_msg}/g, lp_msg);
            row = row.replace(/\${lp_disabled}/g, lp_disabled);
            row = row.replace(/\${lp_disabled_attr}/g, lp_disabled_attr);
            row = row.replace(/\${lp_reason}/g, lp_reason);
            
            let bday_icon = s.is_birthday ? '<i class="fa fa-birthday-cake" style="color: #d63384; margin-left: 6px;" title="Birthday Today!"></i>' : '';
            row = row.replace(/\${birthday_icon}/g, bday_icon);

            let new_student_badge = s.is_new_joiner ? '<span style="background-color: #ff9800; color: white; font-size: 10px; margin-left: 8px; padding: 2px 6px; border-radius: 12px; font-weight: bold;"><i class="fa fa-star"></i> New Student</span>' : '';
            row = row.replace(/\${new_student_badge}/g, new_student_badge);
            
            let temp_batch_badge = s.is_temporary ? `<span style="background-color: #9c27b0; color: white; font-size: 10px; padding: 2px 6px; border-radius: 12px; font-weight: bold;" title="Temporarily moved from Batch ${s.original_batch}"><i class="fa fa-exchange"></i> Actual Batch: ${s.original_batch}</span>` : '';
            row = row.replace(/\${temporary_batch_badge}/g, temp_batch_badge);

            let new_student_name_style = s.is_new_joiner ? 'color: #ff9800; font-weight: bold;' : '';
            row = row.replace(/\${new_student_name_style}/g, new_student_name_style);

            let avatar_html = frappe.get_avatar('avatar-large', s.student_name, s.image).replace('<img ', '<img loading="lazy" ');
            row = row.replace(/\${avatar_html}/g, avatar_html);

            row = row.replace(/\${present_active}/g, s.today_status === 'Present' ? 'active' : '');
            row = row.replace(/\${present_checked}/g, s.today_status === 'Present' ? 'checked' : '');

            row = row.replace(/\${absent_active}/g, s.today_status === 'Absent' ? 'active' : '');
            row = row.replace(/\${absent_checked}/g, s.today_status === 'Absent' ? 'checked' : '');

            row = row.replace(/\${late_active}/g, s.today_status === 'Late' ? 'active' : '');
            row = row.replace(/\${late_checked}/g, s.today_status === 'Late' ? 'checked' : '');

            html += row;
        });

        this.$tbody.html(html);


        this.apply_row_filters();
    }

    update_summary(s) {
        this.summary = s;
        this.wrapper.find('#sum-present').text(s.present);
        this.wrapper.find('#sum-absent').text(s.absent);
        this.wrapper.find('#sum-late').text(s.late);
        this.wrapper.find('#sum-pending').text(s.pending);
    }

    mark_attendance(student, status, $input, late_reason) {
        let date = this.$date.val();
        let args = {
            student: student,
            attendance_date: date,
            status: status
        };
        if(late_reason) args.late_reason = late_reason;

        frappe.call({
            method: 'bb_tution_management.bb_academy.attendance.save_student_attendance',
            args: args,
            callback: (r) => {
                if(r.message && r.message.status === 'success') {
                    frappe.show_alert({message: `Attendance updated for ${student}`, indicator: 'green'}, 3);
                    
                    let $tr = this.$tbody.find(`tr[data-id="${student}"]`);

                    let old_status = $tr.attr('data-current-status');
                    $tr.attr('data-current-status', status);

                    // Also update raw_students array so it persists on toggle
                    let raw_s = this.raw_students.find(x => x.student_id === student);
                    if(raw_s) raw_s.today_status = status;

                    if(!this.student_visible_for_status(status)) {
                        $tr.fadeOut(200, () => {
                            $tr.remove();
                            this.selected.delete(student);
                            this.update_bulk_bar();
                            this.recalc_summary(status, old_status);

                            if(this.$tbody.find('tr.att-student-row').length === 0) {
                                if(this.status_filter) {
                                    this.$tbody.html(this.empty_state_html('fa-info-circle', `No ${this.status_filter} Students`,
                                        `No students match the "${this.status_filter}" filter for this selection.`));
                                } else {
                                    this.$tbody.html(this.empty_state_html('fa-check-circle', 'All Done!',
                                        'Awesome! All attendance has been marked for this date.', 'is-success'));
                                }
                            }
                        });
                    } else {
                        this.recalc_summary(status, old_status);
                    }
                }
            },
            error: (err) => {
                frappe.msgprint('Error saving attendance');
                this.load_students();
            }
        });
    }

    bulk_mark_attendance(status) {
        if(this.selected.size === 0) return;

        let students = [...this.selected];
        let date = this.$date.val();
        let std = this.$std.val();
        let batch = this.$batch.val();

        if(status === 'Late') {
            this.prompt_late_reason(
                (late_reason) => this.submit_bulk_attendance(students, std, batch, date, status, late_reason),
                null,
                {
                    title: 'Mark Late',
                    primary_label: 'Mark Late',
                    description: `Mark ${students.length} selected student(s) as Late. Pick a reason.`
                }
            );
            return;
        }

        frappe.confirm(
            `Mark <b>${students.length}</b> selected student(s) as <b>${status}</b>?`,
            () => this.submit_bulk_attendance(students, std, batch, date, status)
        );
    }

    submit_bulk_attendance(students, std, batch, date, status, late_reason) {
        let args = {
            students: JSON.stringify(students),
            standard: std,
            batch: batch,
            attendance_date: date,
            status: status
        };
        if(late_reason) args.late_reason = late_reason;

        frappe.call({
            method: 'bb_tution_management.bb_academy.attendance.save_bulk_attendance',
            args: args,
            freeze: true,
            callback: (r) => {
                if(r.message && r.message.status === 'success') {
                    frappe.show_alert({message: `Attendance marked ${status} for ${r.message.count} student(s)`, indicator: 'green'}, 3);
                    this.selected.clear();
                    this.load_students();
                }
            },
            error: () => {
                frappe.msgprint('Error saving bulk attendance');
            }
        });
    }

    recalc_summary(status, old_status) {
        if(status && this.summary) {
            if(!old_status) {
                this.summary.pending--;
            } else {
                if(old_status === 'Present') this.summary.present--;
                if(old_status === 'Absent') this.summary.absent--;
                if(old_status === 'Late') this.summary.late--;
            }
            if(status === 'Present') this.summary.present++;
            if(status === 'Absent') this.summary.absent++;
            if(status === 'Late') this.summary.late++;
            this.update_summary(this.summary);
        }
    }

    show_holiday_dialog() {
        let d = new frappe.ui.Dialog({
            title: 'Assign Holiday',
            fields: [
                { fieldname: 'date', fieldtype: 'Date', label: 'Date', reqd: 1, default: this.$date.val() },
                { fieldname: 'holiday_type', fieldtype: 'Select', label: 'Holiday Type', options: "Rain\nGovernment Holiday\nSchool Holiday\nEmergency\nSunday\nKPI Meeting\nOther", reqd: 1 },
                { fieldname: 'reason', fieldtype: 'Small Text', label: 'Reason', reqd: 1 },
                { fieldname: 'scope', fieldtype: 'Select', label: 'Scope', options: "Entire School\nStandard\nStandard + Batch", reqd: 1 },
                { fieldname: 'standard', fieldtype: 'Link', options: 'Standard', label: 'Standard', depends_on: "eval:in_list(['Standard', 'Standard + Batch'], doc.scope)" },
                { fieldname: 'batch', fieldtype: 'Link', options: 'Batch', label: 'Batch', depends_on: "eval:doc.scope=='Standard + Batch'" }
            ],
            primary_action_label: 'Assign Holiday',
            primary_action: (values) => {
                frappe.call({
                    method: 'bb_tution_management.bb_academy.attendance.assign_holiday',
                    args: values,
                    callback: (r) => {
                        if(r.message) {
                            frappe.show_alert({message: 'Holiday assigned successfully', indicator: 'green'});
                            d.hide();
                            if(this.$date.val() === values.date) {
                                this.load_students();
                            }
                        }
                    }
                });
            }
        });
        
        if(this.$std.val()) d.set_value('standard', this.$std.val());
        if(this.$batch.val()) d.set_value('batch', this.$batch.val());
        
        d.show();
    }
}
