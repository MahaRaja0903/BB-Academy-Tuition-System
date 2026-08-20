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
        
        this.setup_ui();
    }

    setup_ui() {
        this.wrapper.html(frappe.render_template("attendance_manager", {}));
        
        this.$std = this.wrapper.find('#att-standard');
        this.$batch = this.wrapper.find('#att-batch');
        this.$date = this.wrapper.find('#att-date');
        this.$search = this.wrapper.find('#att-search');
        this.$tbody = this.wrapper.find('#att-tbody');
        this.$hol_msg = this.wrapper.find('#holiday-message');
        this.$table = this.wrapper.find('#att-table');
        
        // Set date to today
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
            let term = $(e.target).val().toLowerCase();
            this.wrapper.find('.att-student-row').each(function() {
                let txt = $(this).data('id').toLowerCase() + " " + $(this).data('name');
                if(txt.indexOf(term) > -1) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });
        });
        
        this.wrapper.find('#btn-assign-holiday').on('click', () => {
            this.show_holiday_dialog();
        });
        
        // Event delegation for attendance buttons
        this.$tbody.on('change', 'input[type=radio]', (e) => {
            let $input = $(e.target);
            let status = $input.val();
            let student = $input.closest('tr').data('id');
            this.mark_attendance(student, status, $input);
        });
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
                filters: { 'standard': standard },
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
        this.$tbody.html('<tr><td colspan="4" class="text-center text-muted">Select Standard and Batch to load students.</td></tr>');
        this.students = [];
        this.update_summary({present: 0, absent: 0, late: 0, pending: 0});
        this.$hol_msg.hide();
        this.$table.show();
    }

    load_students() {
        let std = this.$std.val();
        let batch = this.$batch.val();
        let date = this.$date.val();
        
        if(!std || !batch || !date) return;
        
        frappe.call({
            method: 'bb_tution_management.bb_academy.attendance.get_attendance_students',
            args: {
                standard: std,
                batch: batch,
                attendance_date: date
            },
            freeze: true,
            callback: (r) => {
                if(r.message) {
                    if(r.message.holiday) {
                        this.show_holiday(r.message.holiday);
                    } else {
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
        this.update_summary({present: 0, absent: 0, late: 0, pending: 0});
        this.wrapper.find('#sum-total').text(0);
    }

    render_students(students, summary) {
        this.$hol_msg.hide();
        this.$table.show();
        this.students = students;
        this.update_summary(summary);
        this.wrapper.find('#sum-total').text(students.length);
        
        if(students.length === 0) {
            this.$tbody.html('<tr><td colspan="4" class="text-center text-muted">No active students found for this Standard and Batch on the selected date.</td></tr>');
            return;
        }
        
        let html = '';
        let template = this.wrapper.find('#att-row-template').html();
        
        students.forEach(s => {
            let row = template;
            row = row.replace(/\${student_id}/g, s.student_id);
            row = row.replace(/\${student_name}/g, s.student_name);
            row = row.replace(/\${student_name_lower}/g, (s.student_name || "").toLowerCase());
            row = row.replace(/\${monthly_absent}/g, s.monthly_absent);
            row = row.replace(/\${monthly_late}/g, s.monthly_late);
            row = row.replace(/\${previous_status}/g, s.previous_status);
            
            row = row.replace(/\${present_active}/g, s.today_status === 'Present' ? 'active' : '');
            row = row.replace(/\${present_checked}/g, s.today_status === 'Present' ? 'checked' : '');
            
            row = row.replace(/\${absent_active}/g, s.today_status === 'Absent' ? 'active' : '');
            row = row.replace(/\${absent_checked}/g, s.today_status === 'Absent' ? 'checked' : '');
            
            row = row.replace(/\${late_active}/g, s.today_status === 'Late' ? 'active' : '');
            row = row.replace(/\${late_checked}/g, s.today_status === 'Late' ? 'checked' : '');
            
            html += row;
        });
        
        this.$tbody.html(html);
        
        // Re-trigger search filter if there's any text
        this.$search.trigger('input');
    }

    update_summary(s) {
        this.summary = s;
        this.wrapper.find('#sum-present').text(s.present);
        this.wrapper.find('#sum-absent').text(s.absent);
        this.wrapper.find('#sum-late').text(s.late);
        this.wrapper.find('#sum-pending').text(s.pending);
    }

    mark_attendance(student, status, $input) {
        let date = this.$date.val();
        
        frappe.call({
            method: 'bb_tution_management.bb_academy.attendance.save_student_attendance',
            args: {
                student: student,
                attendance_date: date,
                status: status
            },
            callback: (r) => {
                if(r.message && r.message.status === 'success') {
                    frappe.show_alert({message: `Attendance updated for ${student}`, indicator: 'green'}, 3);
                    
                    let $tr = this.$tbody.find(`tr[data-id="${student}"]`);
                    $tr.find('.att-absent-count').text(r.message.monthly_absent);
                    $tr.find('.att-late-count').text(r.message.monthly_late);
                    
                    this.recalc_summary();
                }
            },
            error: (err) => {
                frappe.msgprint('Error saving attendance');
                this.load_students();
            }
        });
    }

    recalc_summary() {
        let p=0, a=0, l=0, pend=0;
        this.$tbody.find('.att-student-row').each(function() {
            let val = $(this).find('input[type=radio]:checked').val();
            if(val === 'Present') p++;
            else if(val === 'Absent') a++;
            else if(val === 'Late') l++;
            else pend++;
        });
        this.update_summary({present: p, absent: a, late: l, pending: pend});
    }

    show_holiday_dialog() {
        let d = new frappe.ui.Dialog({
            title: 'Assign Holiday',
            fields: [
                { fieldname: 'date', fieldtype: 'Date', label: 'Date', reqd: 1, default: this.$date.val() },
                { fieldname: 'holiday_type', fieldtype: 'Select', label: 'Holiday Type', options: "Rain\nGovernment Holiday\nSchool Holiday\nEmergency\nOther", reqd: 1 },
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
