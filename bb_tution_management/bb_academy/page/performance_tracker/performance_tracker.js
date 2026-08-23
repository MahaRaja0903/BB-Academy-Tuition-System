frappe.pages['performance-tracker'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Student Performance Tracker',
        single_column: true
    });

    wrapper.performance_manager = new PerformanceManager(wrapper);
}

class PerformanceManager {
    constructor(wrapper) {
        this.wrapper = $(wrapper).find('.layout-main-section');
        this.page = wrapper.page;
        this.students = [];
        this.activity_lists = { bad_activities: [], critical_activities: [] };
        
        this.setup_ui();
        this.fetch_activities();
    }

    setup_ui() {
        // Load html template
        frappe.call({
            method: 'frappe.client.get',
            args: { doctype: 'Page', name: 'performance-tracker' },
            callback: (r) => {
                // Actually we can just load the html file from disk using frappe.render_template if it was compiled, 
                // but since we are not sure, we can fetch it or just use frappe.render_template if we add it to build.json.
                // Wait, in Frappe pages, html is automatically loaded if it's named the same as .js
                // we can just use `frappe.render_template("performance_tracker", {})`
                this.wrapper.html(frappe.render_template("performance_tracker", {}));
                this.init_elements();
            }
        });
    }

    init_elements() {
        this.$std = this.wrapper.find('#perf-standard');
        this.$batch = this.wrapper.find('#perf-batch');
        this.$date = this.wrapper.find('#perf-date');
        this.$search = this.wrapper.find('#perf-search');
        this.$tbody = this.wrapper.find('#perf-tbody');
        this.$table = this.wrapper.find('#perf-table');

        this.$date.val(frappe.datetime.get_today());

        this.load_standards();
        this.bind_events();
    }

    fetch_activities() {
        frappe.call({
            method: 'bb_tution_management.bb_academy.performance.get_activity_lists',
            callback: (r) => {
                if(r.message) {
                    this.activity_lists = r.message;
                }
            }
        });
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
            this.apply_row_filters();
        });

        // Toggle checkbox logic
        this.$tbody.on('change', '.perf-toggle', (e) => {
            let $cb = $(e.currentTarget);
            let $row = $cb.closest('.perf-metric-row');
            let $opts = $row.find('.perf-options');
            if($cb.is(':checked')) {
                $opts.show();
            } else {
                $opts.hide();
                $opts.find('input[type=radio]').prop('checked', false);
                $opts.find('label.active').removeClass('active');
                $opts.find('.bad-activities-input, .critical-activities-input').hide().val('');
            }
        });

        // Discipline logic
        this.$tbody.on('change', 'input[type=radio]', (e) => {
            let $rb = $(e.currentTarget);
            let val = $rb.val();
            let name = $rb.attr('name');
            if(name.startsWith('disc_')) {
                let $opts = $rb.closest('.perf-options');
                $opts.find('.bad-activities-input, .critical-activities-input').hide();
                if(val === 'Bad') {
                    $opts.find('.bad-activities-input').show();
                } else if(val === 'Critical') {
                    $opts.find('.critical-activities-input').show();
                }
            }
        });

        // Activity selector dialog
        this.$tbody.on('focus', '.bad-activities-input', (e) => {
            this.show_activity_dialog(e.currentTarget, 'Bad Activities', this.activity_lists.bad_activities);
        });

        this.$tbody.on('focus', '.critical-activities-input', (e) => {
            this.show_activity_dialog(e.currentTarget, 'Critical Activities', this.activity_lists.critical_activities);
        });

        // Save button
        this.$tbody.on('click', '.btn-save-perf', (e) => {
            let $btn = $(e.currentTarget);
            let $tr = $btn.closest('tr');
            this.save_row($tr);
        });
    }

    show_activity_dialog(input_el, title, options) {
        $(input_el).blur(); // remove focus
        let current_vals = $(input_el).val().split(',').map(s => s.trim()).filter(Boolean);
        
        let fields = options.map(opt => ({
            fieldname: opt.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase(),
            fieldtype: 'Check',
            label: opt,
            default: current_vals.includes(opt) ? 1 : 0
        }));

        let d = new frappe.ui.Dialog({
            title: title,
            fields: fields,
            primary_action_label: 'Select',
            primary_action: (values) => {
                let selected = [];
                for(let key in values) {
                    if(values[key]) {
                        // find original label
                        let f = fields.find(f => f.fieldname === key);
                        if(f) selected.push(f.label);
                    }
                }
                $(input_el).val(selected.join(', '));
                d.hide();
            }
        });
        d.show();
    }

    apply_row_filters() {
        let term = this.$search.val().toLowerCase();
        this.wrapper.find('.perf-student-row').each(function() {
            let txt = $(this).data('id').toLowerCase() + " " + $(this).data('name');
            if(txt.indexOf(term) > -1) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    }

    load_standards() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: { doctype: 'Standard', fields: ['name'], limit_page_length: 0 },
            callback: (r) => {
                if(r.message) {
                    let html = '<option value="">Select Standard</option>';
                    r.message.forEach(d => { html += `<option value="${d.name}">${d.name}</option>`; });
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
            args: { doctype: 'Batch', fields: ['name'], limit_page_length: 0 },
            callback: (r) => {
                let html = '<option value="">Select Batch</option>';
                if(r.message) {
                    r.message.forEach(d => { html += `<option value="${d.name}">${d.name}</option>`; });
                }
                this.$batch.html(html).prop('disabled', false);
            }
        });
    }

    clear_students() {
        this.$tbody.html(`<tr class="att-placeholder-row"><td colspan="3">
            <div class="att-empty-state">
                <div class="att-empty-icon"><i class="fa fa-graduation-cap"></i></div>
                <h4>Select Standard &amp; Batch</h4>
                <p>Choose a Standard and Batch above to load students and track performance.</p>
            </div>
        </td></tr>`);
        this.students = [];
    }

    load_students() {
        let std = this.$std.val();
        let batch = this.$batch.val();
        let date = this.$date.val();

        if(!std || !batch || !date) return;

        this.$tbody.html(`<tr><td colspan="3" class="text-center">Loading...</td></tr>`);

        frappe.call({
            method: 'bb_tution_management.bb_academy.performance.get_performance_students',
            args: { standard: std, batch: batch, date: date },
            callback: (r) => {
                if(r.message) {
                    this.render_students(r.message.students);
                }
            }
        });
    }

    render_students(students) {
        this.students = students;
        if(students.length === 0) {
            this.$tbody.html(`<tr class="att-placeholder-row"><td colspan="3">
                <div class="att-empty-state">
                    <div class="att-empty-icon"><i class="fa fa-graduation-cap"></i></div>
                    <h4>No Students Found</h4>
                    <p>No active students found for this Standard and Batch.</p>
                </div>
            </td></tr>`);
            return;
        }

        let html = '';
        let template = this.wrapper.find('#perf-row-template').html();

        students.forEach(s => {
            let row = template;
            row = row.replace(/\${student_id}/g, s.student_id);
            row = row.replace(/\${student_name}/g, s.student_name);
            row = row.replace(/\${student_name_lower}/g, (s.student_name || "").toLowerCase());
            row = row.replace(/\${gender}/g, s.gender || "");
            row = row.replace(/\${gender_icon}/g, s.gender === 'Female' ? 'fa-female' : (s.gender === 'Male' ? 'fa-male' : ''));
            row = row.replace(/\${gender_icon_class}/g, s.gender === 'Female' ? 'att-gender-icon-female' : (s.gender === 'Male' ? 'att-gender-icon-male' : ''));

            // Study
            row = row.replace(/\${study_checked}/g, s.study ? 'checked' : '');
            row = row.replace(/\${study_display}/g, s.study ? 'block' : 'none');
            row = row.replace(/\${study_good}/g, s.study_performance === 'Good' ? 'active' : '');
            row = row.replace(/\${study_bad}/g, s.study_performance === 'Bad' ? 'active' : '');
            row = row.replace(/\${study_poor}/g, s.study_performance === 'Poor' ? 'active' : '');
            row = row.replace(/\${study_good_c}/g, s.study_performance === 'Good' ? 'checked' : '');
            row = row.replace(/\${study_bad_c}/g, s.study_performance === 'Bad' ? 'checked' : '');
            row = row.replace(/\${study_poor_c}/g, s.study_performance === 'Poor' ? 'checked' : '');

            // Test
            row = row.replace(/\${test_checked}/g, s.test ? 'checked' : '');
            row = row.replace(/\${test_display}/g, s.test ? 'block' : 'none');
            row = row.replace(/\${test_good}/g, s.test_performance === 'Good' ? 'active' : '');
            row = row.replace(/\${test_bad}/g, s.test_performance === 'Bad' ? 'active' : '');
            row = row.replace(/\${test_poor}/g, s.test_performance === 'Poor' ? 'active' : '');
            row = row.replace(/\${test_good_c}/g, s.test_performance === 'Good' ? 'checked' : '');
            row = row.replace(/\${test_bad_c}/g, s.test_performance === 'Bad' ? 'checked' : '');
            row = row.replace(/\${test_poor_c}/g, s.test_performance === 'Poor' ? 'checked' : '');

            // Maths Test
            row = row.replace(/\${mtest_checked}/g, s.maths_test ? 'checked' : '');
            row = row.replace(/\${mtest_display}/g, s.maths_test ? 'block' : 'none');
            row = row.replace(/\${mtest_good}/g, s.maths_test_performance === 'Good' ? 'active' : '');
            row = row.replace(/\${mtest_bad}/g, s.maths_test_performance === 'Bad' ? 'active' : '');
            row = row.replace(/\${mtest_poor}/g, s.maths_test_performance === 'Poor' ? 'active' : '');
            row = row.replace(/\${mtest_good_c}/g, s.maths_test_performance === 'Good' ? 'checked' : '');
            row = row.replace(/\${mtest_bad_c}/g, s.maths_test_performance === 'Bad' ? 'checked' : '');
            row = row.replace(/\${mtest_poor_c}/g, s.maths_test_performance === 'Poor' ? 'checked' : '');

            // Discipline
            row = row.replace(/\${disc_checked}/g, s.discipline ? 'checked' : '');
            row = row.replace(/\${disc_display}/g, s.discipline ? 'block' : 'none');
            row = row.replace(/\${disc_good}/g, s.discipline_performance === 'Good' ? 'active' : '');
            row = row.replace(/\${disc_bad}/g, s.discipline_performance === 'Bad' ? 'active' : '');
            row = row.replace(/\${disc_critical}/g, s.discipline_performance === 'Critical' ? 'active' : '');
            row = row.replace(/\${disc_good_c}/g, s.discipline_performance === 'Good' ? 'checked' : '');
            row = row.replace(/\${disc_bad_c}/g, s.discipline_performance === 'Bad' ? 'checked' : '');
            row = row.replace(/\${disc_critical_c}/g, s.discipline_performance === 'Critical' ? 'checked' : '');

            // Activities
            row = row.replace(/\${bad_act_display}/g, s.discipline_performance === 'Bad' ? 'block' : 'none');
            row = row.replace(/\${crit_act_display}/g, s.discipline_performance === 'Critical' ? 'block' : 'none');
            row = row.replace(/\${bad_activities}/g, s.bad_activities || '');
            row = row.replace(/\${critical_activities}/g, s.critical_activities || '');

            html += row;
        });

        this.$tbody.html(html);
        this.apply_row_filters();
    }

    save_row($tr) {
        let student_id = $tr.data('id');
        let date = this.$date.val();
        
        let data = {
            study: $tr.find('.perf-toggle[data-type="study"]').is(':checked') ? 1 : 0,
            study_performance: $tr.find(`input[name="study_${student_id}"]:checked`).val() || "",
            
            test: $tr.find('.perf-toggle[data-type="test"]').is(':checked') ? 1 : 0,
            test_performance: $tr.find(`input[name="test_${student_id}"]:checked`).val() || "",
            
            maths_test: $tr.find('.perf-toggle[data-type="maths_test"]').is(':checked') ? 1 : 0,
            maths_test_performance: $tr.find(`input[name="mtest_${student_id}"]:checked`).val() || "",
            
            discipline: $tr.find('.perf-toggle[data-type="discipline"]').is(':checked') ? 1 : 0,
            discipline_performance: $tr.find(`input[name="disc_${student_id}"]:checked`).val() || "",
            
            bad_activities: $tr.find('.bad-activities-input').val() || "",
            critical_activities: $tr.find('.critical-activities-input').val() || ""
        };

        let $btn = $tr.find('.btn-save-perf');
        $btn.text('Saving...').prop('disabled', true);

        frappe.call({
            method: 'bb_tution_management.bb_academy.performance.save_student_performance',
            args: {
                student: student_id,
                date: date,
                data: JSON.stringify(data)
            },
            callback: (r) => {
                $btn.text('Save').prop('disabled', false);
                if(r.message && r.message.status === 'success') {
                    frappe.show_alert({message: `Performance updated for ${student_id}`, indicator: 'green'});
                }
            },
            error: () => {
                $btn.text('Save').prop('disabled', false);
                frappe.msgprint('Error saving performance');
            }
        });
    }
}