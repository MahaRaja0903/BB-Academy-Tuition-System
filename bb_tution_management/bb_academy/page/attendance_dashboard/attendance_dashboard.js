frappe.pages['attendance-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Attendance Dashboard',
        single_column: true
    });
    wrapper.attendance_dashboard = new AttendanceDashboard(wrapper);
}

class AttendanceDashboard {
    constructor(wrapper) {
        this.wrapper = $(wrapper).find('.layout-main-section');
        this.charts = {};
        this.setup_ui();
        this.bind_events();
    }

    setup_ui() {
        this.wrapper.html(frappe.render_template("attendance_dashboard", {}));

        this.$root = this.wrapper.find('.attendance-dashboard');
        this.$std = this.wrapper.find('#dash-standard');
        this.$batch = this.wrapper.find('#dash-batch');
        this.$date = this.wrapper.find('#dash-date');

        this.$date.val(frappe.datetime.get_today());

        this.load_standards();
        this.load_data();
    }

    bind_events() {
        this.$std.on('change', () => {
            this.load_batches(this.$std.val());
            this.load_data();
        });

        this.$batch.on('change', () => {
            this.load_data();
        });

        this.$date.on('change', () => {
            this.load_data();
        });

        this.wrapper.find('.stat-card').on('click', (e) => {
            let action = $(e.currentTarget).data('action');
            if(action === 'new-students') {
                frappe.set_route('List', 'Student', {
                    'status': 'Active',
                    'admission_date': ['between', [frappe.datetime.add_days(frappe.datetime.get_today(), -6), frappe.datetime.get_today()]]
                });
            } else if (action === 'today-absent') {
                frappe.set_route('List', 'Student Attendance', {
                    'attendance_date': this.$date.val(),
                    'status': 'Absent'
                });
            } else if (action === 'absent-5') {
                frappe.set_route('query-report', 'Absent Student Report');
            } else if (action === 'late-5') {
                frappe.set_route('query-report', 'Late Entry Report');
            }
        });

        this.wrapper.find('#btn-dashboard-holiday').on('click', () => {
            frappe.set_route('List', 'Attendance Holiday');
        });
    }

    load_standards() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: { doctype: 'Standard', fields: ['name'], limit_page_length: 0 },
            callback: (r) => {
                if(r.message) {
                    let html = '<option value="">All Standards</option>';
                    r.message.forEach(d => { html += `<option value="${d.name}">${d.name}</option>`; });
                    this.$std.html(html);
                }
            }
        });
    }

    load_batches(standard) {
        if(!standard) {
            this.$batch.html('<option value="">All Batches</option>').prop('disabled', true);
            return;
        }
        frappe.call({
            method: 'frappe.client.get_list',
            args: { doctype: 'Batch', fields: ['name'],  limit_page_length: 0 },
            callback: (r) => {
                let html = '<option value="">All Batches</option>';
                if(r.message) {
                    r.message.forEach(d => { html += `<option value="${d.name}">${d.name}</option>`; });
                }
                this.$batch.html(html).prop('disabled', false);
            }
        });
    }

    set_loading(is_loading) {
        this.$root.toggleClass('is-loading', is_loading);
        // #dash-batch is excluded — its disabled state is governed by
        // load_batches() based on whether a Standard is selected, and
        // forcing it enabled here would fight with that.
        this.wrapper.find('#dash-standard, #dash-date, #btn-dashboard-holiday')
            .prop('disabled', is_loading);
    }

    load_data() {
        this.set_loading(true);
        frappe.call({
            method: 'bb_tution_management.bb_academy.attendance.get_attendance_dashboard_data',
            args: {
                standard: this.$std.val(),
                batch: this.$batch.val(),
                date: this.$date.val()
            },
            callback: (r) => {
                if(r.message) {
                    this.render_data(r.message);
                }
            },
            always: () => {
                this.set_loading(false);
            }
        });
    }

    // ------------------------------------------------------------------
    // Small helpers used only for display (never touch the underlying
    // data/values passed to the charts).
    // ------------------------------------------------------------------

    is_mobile() {
        return window.innerWidth < 576;
    }

    is_tablet() {
        return window.innerWidth < 992;
    }

    chart_height(desktop, mobile) {
        return this.is_mobile() ? mobile : desktop;
    }

    toggle_chart_empty(chart_id, empty_id, has_data) {
        this.wrapper.find(`#${chart_id}`).toggle(has_data);
        this.wrapper.find(`#${empty_id}`).toggle(!has_data);
    }

    truncate_label(text, max_len) {
        if(!text) return text;
        return text.length > max_len ? text.slice(0, max_len - 1) + '…' : text;
    }

    // Builds a label array with a bounded number of *visible* tick labels
    // (the rest are replaced with unique invisible placeholders so the axis
    // doesn't overlap) plus a lookup back to the original text for tooltips.
    // All data points/values stay untouched — only tick text is thinned.
    build_thinned_labels(raw_labels, max_visible) {
        let map = {};
        let n = raw_labels.length;

        if(n <= max_visible) {
            raw_labels.forEach(l => { map[l] = l; });
            return { labels: raw_labels.slice(), map };
        }

        let step = Math.ceil(n / max_visible);
        let labels = raw_labels.map((label, i) => {
            if(i % step === 0 || i === n - 1) {
                map[label] = label;
                return label;
            }
            let placeholder = ' '.repeat(i + 1);
            map[placeholder] = label;
            return placeholder;
        });

        return { labels, map };
    }

    render_data(d) {

        this.wrapper.find('#dash-new').text(d.new_students);
        this.wrapper.find('#dash-absent').text(d.today_absent);
        this.wrapper.find('#dash-abs-5').text(d.absent_5_plus);
        this.wrapper.find('#dash-late-5').text(d.late_5_plus);


        let sum = d.today_summary;
        this.wrapper.find('#dash-sum-total').text(sum.total);

        let has_today_data = (sum.total || 0) > 0;
        this.toggle_chart_empty('chart-today-dist', 'empty-today-dist', has_today_data);

        if(this.charts.today) this.charts.today.destroy();
        if(has_today_data) {
            this.charts.today = new frappe.Chart(this.wrapper.find('#chart-today-dist')[0], {
                data: {
                    labels: ['Present', 'Absent', 'Late', 'Pending'],
                    datasets: [{ values: [sum.present, sum.absent, sum.late, sum.pending] }]
                },
                type: 'donut',
                colors: ['#30a66d', '#cc2929', '#e86c13', '#c7c7c7'],
                height: this.chart_height(300, 260),
                tooltipOptions: { formatTooltipY: val => val + ' students' }
            });
        }


        let trend_labels = [];
        let trend_p = [];
        let trend_a = [];


        let datesMap = {};
        (d.trend_raw || []).forEach(r => {
            if(!datesMap[r.attendance_date]) datesMap[r.attendance_date] = { p: 0, a: 0, total: 0 };
            if (r.status === 'Present' || r.status === 'Late') {
                datesMap[r.attendance_date].p += r.cnt;
            } else if (r.status === 'Absent') {
                datesMap[r.attendance_date].a += r.cnt;
            }
            datesMap[r.attendance_date].total += r.cnt;
        });

        Object.keys(datesMap).sort().forEach(dt => {
            trend_labels.push(frappe.datetime.str_to_user(dt));
            let v = datesMap[dt];
            if(v.total > 0) {
                trend_p.push(Math.round((v.p / v.total) * 100));
            } else {
                trend_p.push(0);
            }
        });

        let has_trend_data = trend_labels.length > 0;
        this.toggle_chart_empty('chart-30-days', 'empty-30-days', has_trend_data);

        if(this.charts.trend) this.charts.trend.destroy();
        if(has_trend_data) {
            let trend_max_visible = this.is_mobile() ? 6 : (this.is_tablet() ? 8 : 12);
            let thinned = this.build_thinned_labels(trend_labels, trend_max_visible);

            this.charts.trend = new frappe.Chart(this.wrapper.find('#chart-30-days')[0], {
                data: {
                    labels: thinned.labels,
                    datasets: [{ name: 'Attendance %', values: trend_p }]
                },
                type: 'line',
                colors: ['#007be0'],
                height: this.chart_height(320, 280),
                tooltipOptions: {
                    formatTooltipX: label => thinned.map[label] || label,
                    formatTooltipY: val => val + '%'
                }
            });
        }


        let sb_title = this.$std.val() ? 'Attendance by Batch' : 'Attendance by Standard';
        this.wrapper.find('#chart-std-title').text(sb_title);

        let sb_labels = [];
        let sb_values = [];
        let sb_map = {};
        let sb_data = this.$std.val() ? d.batch_summary : d.standard_summary;

        (sb_data || []).forEach(r => {
            let key = this.$std.val() ? r.batch : r.standard;
            if(!sb_map[key]) sb_map[key] = { p: 0, total: 0 };
            if(r.status === 'Present' || r.status === 'Late') {
                sb_map[key].p += r.cnt;
            }
            sb_map[key].total += r.cnt;
        });

        Object.keys(sb_map).sort().forEach(k => {
            sb_labels.push(k);
            let v = sb_map[k];
            sb_values.push(v.total > 0 ? Math.round((v.p / v.total) * 100) : 0);
        });

        let has_sb_data = sb_labels.length > 0;
        this.toggle_chart_empty('chart-standard', 'empty-standard', has_sb_data);

        if(this.charts.standard) this.charts.standard.destroy();
        if(has_sb_data) {
            let sb_max_visible = this.is_mobile() ? 6 : (this.is_tablet() ? 10 : 20);
            let sb_thinned = this.build_thinned_labels(sb_labels, sb_max_visible);

            this.charts.standard = new frappe.Chart(this.wrapper.find('#chart-standard')[0], {
                data: {
                    labels: sb_thinned.labels,
                    datasets: [{ name: 'Attendance %', values: sb_values }]
                },
                type: 'bar',
                colors: ['#007be0'],
                height: this.chart_height(320, 280),
                tooltipOptions: {
                    formatTooltipX: label => sb_thinned.map[label] || label,
                    formatTooltipY: val => val + '%'
                }
            });
        }


        let abs_name_map = {};
        let abs_max_len = this.is_mobile() ? 10 : 16;
        let abs_labels = (d.top_absent || []).map(r => {
            let short = this.truncate_label(r.student_name, abs_max_len);
            abs_name_map[short] = r.student_name;
            return short;
        });
        let abs_values = (d.top_absent || []).map(r => r.absent_count);

        let has_abs_data = abs_labels.length > 0;
        this.toggle_chart_empty('chart-top-absent', 'empty-top-absent', has_abs_data);

        if(this.charts.top_absent) this.charts.top_absent.destroy();
        if(has_abs_data) {
            this.charts.top_absent = new frappe.Chart(this.wrapper.find('#chart-top-absent')[0], {
                data: {
                    labels: abs_labels,
                    datasets: [{ name: 'Days', values: abs_values }]
                },
                type: 'bar',
                colors: ['#cc2929'],
                height: this.chart_height(320, 280),
                tooltipOptions: {
                    formatTooltipX: label => abs_name_map[label] || label
                }
            });
        }


        let late_name_map = {};
        let late_max_len = this.is_mobile() ? 10 : 16;
        let late_labels = (d.top_late || []).map(r => {
            let short = this.truncate_label(r.student_name, late_max_len);
            late_name_map[short] = r.student_name;
            return short;
        });
        let late_values = (d.top_late || []).map(r => r.late_count);

        let has_late_data = late_labels.length > 0;
        this.toggle_chart_empty('chart-top-late', 'empty-top-late', has_late_data);

        if(this.charts.top_late) this.charts.top_late.destroy();
        if(has_late_data) {
            this.charts.top_late = new frappe.Chart(this.wrapper.find('#chart-top-late')[0], {
                data: {
                    labels: late_labels,
                    datasets: [{ name: 'Days', values: late_values }]
                },
                type: 'bar',
                colors: ['#e86c13'],
                height: this.chart_height(320, 280),
                tooltipOptions: {
                    formatTooltipX: label => late_name_map[label] || label
                }
            });
        }
    }
}
