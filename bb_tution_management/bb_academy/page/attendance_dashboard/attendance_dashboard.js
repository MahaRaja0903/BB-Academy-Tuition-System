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
        frappe.require('attendance_dashboard.html', () => {
            this.setup_ui();
            this.bind_events();
        });
    }

    setup_ui() {
        this.wrapper.html(frappe.render_template("attendance_dashboard", {}));
        
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
            args: { doctype: 'Batch', fields: ['name'], filters: { 'standard': standard }, limit_page_length: 0 },
            callback: (r) => {
                let html = '<option value="">All Batches</option>';
                if(r.message) {
                    r.message.forEach(d => { html += `<option value="${d.name}">${d.name}</option>`; });
                }
                this.$batch.html(html).prop('disabled', false);
            }
        });
    }

    load_data() {
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
            }
        });
    }
    
    render_data(d) {
        // KPIs
        this.wrapper.find('#dash-new').text(d.new_students);
        this.wrapper.find('#dash-absent').text(d.today_absent);
        this.wrapper.find('#dash-abs-5').text(d.absent_5_plus);
        this.wrapper.find('#dash-late-5').text(d.late_5_plus);
        
        // Distribution Chart
        let sum = d.today_summary;
        this.wrapper.find('#dash-sum-total').text(sum.total);
        
        if(this.charts.today) this.charts.today.destroy();
        this.charts.today = new frappe.Chart(this.wrapper.find('#chart-today-dist')[0], {
            data: {
                labels: ['Present', 'Absent', 'Late', 'Pending'],
                datasets: [{ values: [sum.present, sum.absent, sum.late, sum.pending] }]
            },
            type: 'donut',
            colors: ['#28a745', '#dc3545', '#6c757d', '#ffc107'],
            height: 200,
            tooltipOptions: { formatTooltipY: d => d + ' students' }
        });
        
        // 30 Days Trend Chart
        let trend_labels = [];
        let trend_p = [];
        let trend_a = [];
        
        // Group trend_raw by date
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
        
        if(this.charts.trend) this.charts.trend.destroy();
        this.charts.trend = new frappe.Chart(this.wrapper.find('#chart-30-days')[0], {
            data: {
                labels: trend_labels,
                datasets: [{ name: 'Attendance %', values: trend_p }]
            },
            type: 'line',
            colors: ['#007bff'],
            height: 200,
            tooltipOptions: { formatTooltipY: d => d + '%' }
        });
        
        // Standard / Batch Chart
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
        
        if(this.charts.standard) this.charts.standard.destroy();
        this.charts.standard = new frappe.Chart(this.wrapper.find('#chart-standard')[0], {
            data: {
                labels: sb_labels,
                datasets: [{ name: 'Attendance %', values: sb_values }]
            },
            type: 'bar',
            colors: ['#17a2b8'],
            height: 200,
            tooltipOptions: { formatTooltipY: d => d + '%' }
        });
        
        // Top 10 Absent Chart
        let abs_labels = (d.top_absent || []).map(r => r.student_name);
        let abs_values = (d.top_absent || []).map(r => r.absent_count);
        
        if(this.charts.top_absent) this.charts.top_absent.destroy();
        this.charts.top_absent = new frappe.Chart(this.wrapper.find('#chart-top-absent')[0], {
            data: { labels: abs_labels, datasets: [{ name: 'Days', values: abs_values }] },
            type: 'bar',
            colors: ['#dc3545'],
            height: 250
        });
        
        // Top 10 Late Chart
        let late_labels = (d.top_late || []).map(r => r.student_name);
        let late_values = (d.top_late || []).map(r => r.late_count);
        
        if(this.charts.top_late) this.charts.top_late.destroy();
        this.charts.top_late = new frappe.Chart(this.wrapper.find('#chart-top-late')[0], {
            data: { labels: late_labels, datasets: [{ name: 'Days', values: late_values }] },
            type: 'bar',
            colors: ['#6c757d'],
            height: 250
        });
    }
}
