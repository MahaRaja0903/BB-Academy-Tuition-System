frappe.pages['late_permission'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Late Permission Manager',
        single_column: true
    });

    wrapper.late_permission_manager = new LatePermissionManager(wrapper);
}

class LatePermissionManager {
    constructor(wrapper) {
        this.wrapper = $(wrapper).find('.layout-main-section');
        this.page = wrapper.page;
        this.setup_ui();
    }

    setup_ui() {
        this.wrapper.html(frappe.render_template("late_permission", {}));

        this.$std = this.wrapper.find('#lp-standard');
        this.$batch = this.wrapper.find('#lp-batch');
        this.$gender = this.wrapper.find('#lp-gender');
        this.$date = this.wrapper.find('#lp-date');
        this.$tbody = this.wrapper.find('#lp-tbody');

        this.$date.val(frappe.datetime.get_today());

        this.load_standards();
        this.bind_events();
    }

    bind_events() {
        this.$std.on('change', () => {
            let val = this.$std.val();
            if(val) {
                this.load_batches(val);
            } else {
                this.$batch.empty().append('<option value="">Select Batch</option>').prop('disabled', true);
            }
            this.load_students();
        });

        this.$batch.on('change', () => this.load_students());
        this.$gender.on('change', () => this.load_students());
        
        this.$date.on('change', () => this.load_students());

        this.wrapper.find('#btn-prev-day').on('click', () => {
            this.$date.val(frappe.datetime.add_days(this.$date.val(), -1));
            this.load_students();
        });

        this.wrapper.find('#btn-next-day').on('click', () => {
            this.$date.val(frappe.datetime.add_days(this.$date.val(), 1));
            this.load_students();
        });
        
        this.$tbody.on('click', '.btn-grant-permission', (e) => {
            let student = $(e.currentTarget).closest('tr').data('id');
            this.prompt_permission(student);
        });
        
        this.$tbody.on('click', '.btn-revoke-permission', (e) => {
            let student = $(e.currentTarget).closest('tr').data('id');
            this.revoke_permission(student);
        });
    }

    load_standards() {
        frappe.call({
            method: "frappe.client.get_list",
            args: { doctype: "Standard", fields: ["name"] },
            callback: (r) => {
                if(r.message) {
                    let opts = '<option value="">Select Standard</option>';
                    r.message.forEach(d => { opts += `<option value="${d.name}">${d.name}</option>`; });
                    this.$std.html(opts);
                }
            }
        });
    }

    load_batches(standard) {
        frappe.call({
            method: "frappe.client.get_list",
            args: { doctype: "Batch", filters: { standard: standard }, fields: ["name"] },
            callback: (r) => {
                let opts = '<option value="">Select Batch</option>';
                if(r.message) {
                    r.message.forEach(d => { opts += `<option value="${d.name}">${d.name}</option>`; });
                    this.$batch.html(opts).prop('disabled', false);
                } else {
                    this.$batch.html(opts).prop('disabled', true);
                }
            }
        });
    }

    load_students() {
        let std = this.$std.val();
        let batch = this.$batch.val();
        let gender = this.$gender.val();
        let date = this.$date.val();

        if(!std || !batch || !date) {
            this.$tbody.html('<tr><td colspan="4" class="text-center">Select Standard and Batch</td></tr>');
            return;
        }

        frappe.call({
            method: 'bb_tution_management.bb_academy.late_permission.get_students_for_late_permission',
            args: { standard: std, batch: batch, date: date, gender: gender === 'All' ? '' : gender },
            callback: (r) => {
                if(r.message && r.message.students) {
                    this.render_students(r.message.students);
                }
            }
        });
    }

    render_students(students) {
        if(students.length === 0) {
            this.$tbody.html('<tr><td colspan="4" class="text-center">No active students found.</td></tr>');
            return;
        }

        let html = '';
        let tmpl = this.wrapper.find('#lp-row-template').html();

        students.forEach(s => {
            let row = tmpl;
            row = row.replace(/\${student_id}/g, s.name);
            row = row.replace(/\${student_name}/g, s.student_name);
            
            if(s.has_permission) {
                row = row.replace(/\${status_badge}/g, `<span class="badge badge-success">Permission Granted (${s.late_reason})</span>`);
                row = row.replace(/\${action_button}/g, `<button class="btn btn-xs btn-danger btn-revoke-permission">Revoke</button>`);
            } else {
                row = row.replace(/\${status_badge}/g, `<span class="badge badge-secondary">None</span>`);
                row = row.replace(/\${action_button}/g, `<button class="btn btn-xs btn-primary btn-grant-permission">Grant Permission</button>`);
            }

            html += row;
        });

        this.$tbody.html(html);
    }
    
    prompt_permission(student) {
        frappe.prompt([
            {
                fieldname: 'late_reason',
                fieldtype: 'Select',
                label: 'Late Reason',
                options: 'Traffic\nHealth Issue\nFamily Emergency\nOther',
                reqd: 1
            }
        ], (values) => {
            frappe.call({
                method: 'bb_tution_management.bb_academy.late_permission.grant_late_permission',
                args: {
                    student: student,
                    date: this.$date.val(),
                    late_reason: values.late_reason
                },
                callback: (r) => {
                    if(r.message === 'success') {
                        frappe.show_alert({message: 'Permission Granted', indicator: 'green'});
                        this.load_students();
                    }
                }
            })
        }, 'Grant Late Permission', 'Grant');
    }
    
    revoke_permission(student) {
        frappe.confirm('Are you sure you want to revoke late permission for this student?', () => {
            frappe.call({
                method: 'bb_tution_management.bb_academy.late_permission.revoke_late_permission',
                args: {
                    student: student,
                    date: this.$date.val()
                },
                callback: (r) => {
                    if(r.message === 'success') {
                        frappe.show_alert({message: 'Permission Revoked', indicator: 'green'});
                        this.load_students();
                    }
                }
            })
        });
    }
}
