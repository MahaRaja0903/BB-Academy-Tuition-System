import frappe

def create_print_format():
    html_content = """
<style>
    .fee-tracking-container {
        font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333;
        padding: 30px;
        background-color: #f9fafb;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Top Card */
    .student-card {
        display: flex;
        align-items: center;
        background: #ffffff;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 30px;
        gap: 24px;
    }
    .student-image {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        object-fit: cover;
        background-color: #e5e7eb;
        border: 4px solid #f3f4f6;
    }
    .student-info {
        flex: 1;
    }
    .student-name {
        font-size: 24px;
        font-weight: 700;
        color: #111827;
        margin: 0 0 8px 0;
    }
    .student-meta {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    .meta-item {
        display: flex;
        flex-direction: column;
    }
    .meta-label {
        font-size: 12px;
        text-transform: uppercase;
        color: #6b7280;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .meta-value {
        font-size: 14px;
        color: #374151;
        font-weight: 500;
    }

    /* Summary and Legend */
    .summary-legend-wrapper {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 24px;
        flex-wrap: wrap;
        gap: 20px;
    }
    .summary-box {
        display: flex;
        gap: 16px;
    }
    .stat-card {
        background: #fff;
        padding: 12px 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        text-align: center;
    }
    .stat-val {
        font-size: 20px;
        font-weight: 700;
        color: #111827;
    }
    .stat-label {
        font-size: 12px;
        color: #6b7280;
        font-weight: 500;
    }
    .legend {
        display: flex;
        gap: 16px;
        background: #fff;
        padding: 12px 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: #4b5563;
        font-weight: 500;
    }
    .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    .dot-early { background-color: #10b981; } /* Green */
    .dot-mid { background-color: #f59e0b; } /* Orange */
    .dot-late { background-color: #ef4444; } /* Red */
    .dot-unpaid { background-color: #fee2e2; border: 1px solid #f87171; } /* Light Red */
    .dot-notjoined { background-color: #e5e7eb; } /* Grey */

    /* Timeline Grid */
    .timeline-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
    }
    @media (max-width: 1024px) {
        .timeline-grid { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 768px) {
        .timeline-grid { grid-template-columns: repeat(2, 1fr); }
        .student-card { flex-direction: column; text-align: center; }
        .student-meta { justify-content: center; }
    }
    @media (max-width: 480px) {
        .timeline-grid { grid-template-columns: 1fr; }
    }

    .month-card {
        background: #fff;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        border: 1px solid #f3f4f6;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        cursor: default;
    }
    .month-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .mc-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .mc-month {
        font-size: 18px;
        font-weight: 700;
        color: #1f2937;
    }
    .mc-icon {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 12px;
    }
    
    .mc-status {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 12px;
    }
    .mc-details {
        font-size: 13px;
        color: #6b7280;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .mc-details span {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* Status Colors */
    /* Not Joined */
    .card-notjoined { background-color: #f9fafb; border-color: #e5e7eb; }
    .card-notjoined .mc-month { color: #9ca3af; }
    .card-notjoined .mc-status { background: #f3f4f6; color: #6b7280; }
    .card-notjoined .mc-icon { background: #d1d5db; }
    
    /* Not Paid */
    .card-notpaid { background-color: #fffaf9; border-color: #fecaca; }
    .card-notpaid .mc-status { background: #fee2e2; color: #b91c1c; }
    .card-notpaid .mc-icon { background: #ef4444; }

    /* Paid Early (<10) */
    .card-early .mc-status { background: #d1fae5; color: #065f46; }
    .card-early .mc-icon { background: #10b981; }

    /* Paid Mid (10-15) */
    .card-mid .mc-status { background: #fef3c7; color: #92400e; }
    .card-mid .mc-icon { background: #f59e0b; }

    /* Paid Late (>15) */
    .card-late .mc-status { background: #fee2e2; color: #991b1b; }
    .card-late .mc-icon { background: #ef4444; }

    /* Partial */
    .card-partial .mc-status { background: #e0e7ff; color: #3730a3; }
    .card-partial .mc-icon { background: #6366f1; }

    /* Tooltip */
    .tooltip-text {
        visibility: hidden;
        width: max-content;
        background-color: #1f2937;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px 10px;
        position: absolute;
        z-index: 1;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 12px;
        font-weight: normal;
        margin-bottom: 5px;
    }
    .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #1f2937 transparent transparent transparent;
    }
    .month-card:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
</style>

{% set ad_date = frappe.utils.getdate(doc.admission_date) if doc.admission_date else frappe.utils.today() %}
{% set ad_month_num = ad_date.month %}
{% set ad_ac_index = ad_month_num - 4 if ad_month_num >= 4 else ad_month_num + 8 %}

{% set pay_dict = {} %}
{% for row in doc.payment_details %}
    {% set _ = pay_dict.update({row.month: row}) %}
{% endfor %}

{% set ns = namespace(paid=0, remaining=0, late=0) %}
{% set months = ['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March'] %}

{% for m in months %}
    {% set loop_idx = loop.index0 %}
    {% set p = pay_dict.get(m) %}
    
    {% set status = 'Not Paid' %}
    {% set pd_date = None %}
    
    {% if p %}
        {% set status = p.status %}
        {% set pd_date = p.date %}
    {% else %}
        {% if loop_idx < ad_ac_index %}
            {% set status = 'Not Joined' %}
        {% else %}
            {% set status = 'Not Paid' %}
        {% endif %}
    {% endif %}

    {% if status == 'Paid' %}
        {% set ns.paid = ns.paid + 1 %}
        {% if pd_date %}
            {% set d = frappe.utils.getdate(pd_date).day %}
            {% if d > 15 %}
                {% set ns.late = ns.late + 1 %}
            {% endif %}
        {% endif %}
    {% elif status in ['Not Paid', 'Partial'] %}
        {% set ns.remaining = ns.remaining + 1 %}
    {% endif %}
{% endfor %}

<div class="fee-tracking-container">
    <!-- Top Card -->
    <div class="student-card">
        <img src="{{ doc.image or '/assets/frappe/images/default-avatar.png' }}" alt="Student Image" class="student-image">
        <div class="student-info">
            <h2 class="student-name">{{ doc.student_name }}</h2>
            <div class="student-meta">
                <div class="meta-item">
                    <span class="meta-label">Admission Date</span>
                    <span class="meta-value">{{ frappe.utils.formatdate(doc.admission_date) if doc.admission_date else 'N/A' }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Standard</span>
                    <span class="meta-value">{{ doc.standard }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Current Batch</span>
                    <span class="meta-value">{{ doc.current_batch }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Academic Year</span>
                    <span class="meta-value">{{ doc.academic_year or 'Current' }}</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Summary & Legend -->
    <div class="summary-legend-wrapper">
        <div class="summary-box">
            <div class="stat-card">
                <div class="stat-val text-emerald-600">{{ ns.paid }}</div>
                <div class="stat-label">Months Paid</div>
            </div>
            <div class="stat-card">
                <div class="stat-val text-red-500">{{ ns.remaining }}</div>
                <div class="stat-label">Remaining</div>
            </div>
            <div class="stat-card">
                <div class="stat-val text-orange-500">{{ ns.late }}</div>
                <div class="stat-label">Late Payments</div>
            </div>
        </div>
        
        <div class="legend">
            <div class="legend-item"><div class="dot dot-early"></div> Early (&lt;10th)</div>
            <div class="legend-item"><div class="dot dot-mid"></div> Mid (10-15)</div>
            <div class="legend-item"><div class="dot dot-late"></div> Late (&gt;15)</div>
            <div class="legend-item"><div class="dot dot-unpaid"></div> Pending</div>
            <div class="legend-item"><div class="dot dot-notjoined"></div> Not Joined</div>
        </div>
    </div>

    <!-- Timeline Grid -->
    <div class="timeline-grid">
        {% for m in months %}
            {% set loop_idx = loop.index0 %}
            {% set p = pay_dict.get(m) %}
            
            {% set status = 'Not Paid' %}
            {% set pd_date = None %}
            {% set amt_paid = 0 %}
            {% set card_class = 'card-notpaid' %}
            {% set icon = '⏳' %}
            
            {% if p %}
                {% set status = p.status %}
                {% set pd_date = p.date %}
                {% set amt_paid = p.amount_paid or 0 %}
            {% else %}
                {% if loop_idx < ad_ac_index %}
                    {% set status = 'Not Joined' %}
                {% else %}
                    {% set status = 'Not Paid' %}
                {% endif %}
            {% endif %}

            {% if status == 'Not Joined' %}
                {% set card_class = 'card-notjoined' %}
                {% set icon = '🚫' %}
            {% elif status == 'Paid' %}
                {% set icon = '✔' %}
                {% if pd_date %}
                    {% set d = frappe.utils.getdate(pd_date).day %}
                    {% if d < 10 %}
                        {% set card_class = 'card-early' %}
                    {% elif d <= 15 %}
                        {% set card_class = 'card-mid' %}
                    {% else %}
                        {% set card_class = 'card-late' %}
                    {% endif %}
                {% else %}
                    {% set card_class = 'card-early' %}
                {% endif %}
            {% elif status == 'Partial' %}
                {% set card_class = 'card-partial' %}
                {% set icon = '◐' %}
            {% endif %}

            <div class="month-card {{ card_class }}">
                {% if pd_date and status in ['Paid', 'Partial'] %}
                <div class="tooltip-text">Paid on {{ frappe.utils.formatdate(pd_date) }}</div>
                {% endif %}
                
                <div class="mc-header">
                    <div class="mc-month">{{ m[:3] }}</div>
                    <div class="mc-icon">{{ icon }}</div>
                </div>
                <div class="mc-status">{{ status }}</div>
                
                <div class="mc-details">
                    {% if status not in ['Not Joined'] %}
                        <span>🏠 {{ doc.current_batch }}</span>
                    {% endif %}
                    
                    {% if status in ['Paid', 'Partial'] and pd_date %}
                        <span>📅 {{ frappe.utils.formatdate(pd_date) }}</span>
                    {% elif status == 'Not Paid' %}
                        <span>⚠️ Payment Pending</span>
                    {% elif status == 'Not Joined' %}
                        <span>-</span>
                    {% endif %}
                </div>
            </div>
        {% endfor %}
    </div>
</div>
"""

    if not frappe.db.exists("Print Format", "Student Fee Tracking"):
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "name": "Student Fee Tracking",
            "doc_type": "Student",
            "module": "BB Academy",
            "custom_format": 1,
            "standard": "Yes",
            "print_format_builder": 0,
            "html": html_content
        })
        doc.insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("Print Format", "Student Fee Tracking")
        doc.html = html_content
        doc.save(ignore_permissions=True)
    
    frappe.db.commit()
    print("Successfully created/updated 'Student Fee Tracking' Print Format.")

if __name__ == "__main__":
    frappe.init(site="bb_tution_management")
    frappe.connect()
    create_print_format()
    frappe.destroy()

