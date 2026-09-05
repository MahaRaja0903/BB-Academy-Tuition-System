import frappe

def create_print_formats():
    # Fee Invoice Print Format
    fee_invoice_html = """
<style>
    .invoice-container {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333;
        margin: 0;
        padding: 20px;
    }
    .invoice-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 2px solid #0056b3;
        padding-bottom: 20px;
        margin-bottom: 20px;
    }
    .invoice-header h1 {
        color: #0056b3;
        margin: 0;
        font-size: 32px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .company-details p {
        margin: 2px 0;
        color: #666;
    }
    .invoice-details-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .invoice-details-box table {
        width: 100%;
        border-collapse: collapse;
    }
    .invoice-details-box td {
        padding: 5px;
    }
    .invoice-details-box .label {
        font-weight: bold;
        color: #555;
        width: 40%;
    }
    .student-info {
        margin-top: 20px;
        margin-bottom: 30px;
    }
    .student-info h3 {
        margin-top: 0;
        color: #0056b3;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }
    .fee-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 30px;
    }
    .fee-table th {
        background-color: #0056b3;
        color: white;
        padding: 12px;
        text-align: left;
    }
    .fee-table th.right, .fee-table td.right {
        text-align: right;
    }
    .fee-table td {
        padding: 12px;
        border-bottom: 1px solid #eee;
    }
    .fee-table tr:last-child td {
        border-bottom: 2px solid #0056b3;
    }
    .totals-box {
        float: right;
        width: 40%;
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .totals-box table {
        width: 100%;
    }
    .totals-box td {
        padding: 8px 0;
    }
    .totals-box .total-row {
        font-weight: bold;
        font-size: 1.2em;
        color: #0056b3;
        border-top: 1px solid #ddd;
        padding-top: 10px;
    }
    .status-stamp {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        text-transform: uppercase;
        font-size: 0.9em;
    }
    .status-Paid { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .status-Unpaid { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .status-Partially { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    .status-Draft { background-color: #e2e3e5; color: #383d41; border: 1px solid #d6d8db; }
</style>

<div class="invoice-container">
    <div class="row">
        <div class="col-xs-6">
            <div class="invoice-header">
                <h1>FEE INVOICE</h1>
            </div>
            <div class="company-details">
                <h3 style="margin-top: 0;">BB Academy</h3>
                <p>Tuition Center Management</p>
            </div>
        </div>
        <div class="col-xs-6 text-right">
            <div class="invoice-details-box">
                <table>
                    <tr><td class="label text-left">Invoice No:</td><td class="text-right">{{ doc.name }}</td></tr>
                    <tr><td class="label text-left">Date:</td><td class="text-right">{{ frappe.utils.formatdate(doc.invoice_date) }}</td></tr>
                    <tr><td class="label text-left">Due Date:</td><td class="text-right">{{ frappe.utils.formatdate(doc.due_date) if doc.due_date else '' }}</td></tr>
                    <tr>
                        <td class="label text-left">Status:</td>
                        <td class="text-right">
                            {% set status_class = "status-Partially" if doc.status == "Partially Paid" else "status-" + doc.status %}
                            <span class="status-stamp {{ status_class }}">{{ doc.status }}</span>
                        </td>
                    </tr>
                    <tr><td class="label text-left">Fee Month:</td><td class="text-right">{% set months = [] %}
{% for d in doc.fees_details %}
    {% if d.month and d.month not in months %}
        {% set _ = months.append(d.month) %}
    {% endif %}
{% endfor %}
{{ months | join(', ') }}</td></tr>
                </table>
            </div>
        </div>
    </div>

    <div class="row student-info">
        <div class="col-xs-12">
            <h3>Student Information</h3>
            <table style="width: 100%;">
                <tr>
                    <td style="width: 15%;"><strong>ID:</strong></td>
                    <td style="width: 35%;">{{ doc.student }}</td>
                    <td style="width: 15%;"><strong>Standard:</strong></td>
                    <td style="width: 35%;">{{ doc.standard }}</td>
                </tr>
                <tr>
                    <td><strong>Name:</strong></td>
                    <td>{{ doc.student_name }}</td>
                    <td><strong>Batch:</strong></td>
                    <td>{{ doc.batch }}</td>
                </tr>
            </table>
        </div>
    </div>

    <table class="fee-table">
        <thead>
            <tr>
                <th style="width: 5%;">#</th>
                <th style="width: 65%;">Description</th>
                <th class="right" style="width: 30%;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {% if doc.items %}
                {% for item in doc.items %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ item.description }}</td>
                    <td class="right">{{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(item.amount) }}</td>
                </tr>
                {% endfor %}
            {% else %}
                <tr>
                    <td>1</td>
                    <td>{% set months = [] %}
{% for d in doc.fees_details %}
    {% if d.month and d.month not in months %}
        {% set _ = months.append(d.month) %}
    {% endif %}
{% endfor %}
{{ months | join(', ') }} Monthly Fee</td>
                    <td class="right">{{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(doc.monthly_fee) }}</td>
                </tr>
                {% if doc.arrears_amount and doc.arrears_amount > 0 %}
                <tr>
                    <td>2</td>
                    <td>Arrears Amount</td>
                    <td class="right">{{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(doc.arrears_amount) }}</td>
                </tr>
                {% endif %}
            {% endif %}
        </tbody>
    </table>

    <div class="row">
        <div class="col-xs-6">
            <p style="color: #666; font-size: 0.9em; margin-top: 20px;">
                <strong>Note:-</strong><br>
                *Fee once paid is non-refundable under any circumstances.<br><br>
                *Fee is non-transferable to the next academic year.<br><br>
                *Fee non-transferable to another person.
            </p>
        </div>
        <div class="col-xs-6">
            <div class="totals-box">
                <table>
                    {% set g_total = doc.grand_total if doc.grand_total else (doc.monthly_fee + (doc.arrears_amount or 0)) %}
                    <tr>
                        <td>Grand Total:</td>
                        <td class="text-right">{{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(g_total) }}</td>
                    </tr>
                    <tr>
                        <td>Paid Amount:</td>
                        <td class="text-right">{{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(doc.paid_amount or 0) }}</td>
                    </tr>
                    <tr>
                        <td class="total-row">Outstanding:</td>
                        <td class="total-row text-right">{{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(doc.outstanding_amount) }}</td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
</div>
"""

    if not frappe.db.exists("Print Format", "Fee Invoice Modern Print"):
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "name": "Fee Invoice Modern Print",
            "doc_type": "Fee Invoice",
            "module": "BB Academy",
            "custom_format": 1,
            "standard": "Yes",
            "print_format_builder": 0,
            "html": fee_invoice_html
        })
        doc.insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("Print Format", "Fee Invoice Modern Print")
        doc.html = fee_invoice_html
        doc.save(ignore_permissions=True)


    # Fees Payment Entry Print Format
    payment_html = """
<style>
    .receipt-container {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333;
        margin: 0;
        padding: 20px;
    }
    .receipt-header {
        text-align: center;
        border-bottom: 2px dashed #ccc;
        padding-bottom: 20px;
        margin-bottom: 20px;
    }
    .receipt-header h1 {
        color: #28a745;
        margin: 0;
        font-size: 28px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .receipt-header h3 {
        margin: 5px 0 0 0;
        color: #555;
    }
    .info-card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #eee;
        margin-bottom: 10px;
    }
    .info-card table {
        width: 100%;
    }
    .info-card td {
        padding: 8px 0;
    }
    .info-card .label {
        color: #666;
        font-size: 0.9em;
        text-transform: uppercase;
        width: 40%;
    }
    .info-card .val {
        font-weight: bold;
        color: #333;
        text-align: right;
    }
    .amount-box {
        text-align: center;
        background-color: #e8f5e9;
        border: 2px solid #4caf50;
        border-radius: 10px;
        padding: 20px;
        margin: 30px 0;
    }
    .amount-box h2 {
        color: #2e7d32;
        margin: 0;
        font-size: 36px;
    }
    .amount-box p {
        margin: 5px 0 0 0;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .footer-notes {
        margin-top: 40px;
        text-align: center;
        color: #777;
        font-size: 0.9em;
        border-top: 1px solid #eee;
        padding-top: 20px;
    }
</style>

<div class="receipt-container">
    <div class="receipt-header">
        <h1>PAYMENT RECEIPT</h1>
        <h3>BB Academy</h3>
    </div>

    <div class="row">
        <div class="col-xs-6">
            <div class="info-card">
                <table>
                    <tr><td class="label">Receipt No:</td><td class="val">{{ doc.name }}</td></tr>
                    <tr><td class="label">Date:</td><td class="val">{{ frappe.utils.formatdate(doc.payment_date) }}</td></tr>
                    <tr><td class="label">Payment Mode:</td><td class="val">{{ doc.payment_mode }}</td></tr>
                    <tr><td class="label">Invoice Ref:</td><td class="val">{{ doc.fee_invoice }}</td></tr>
                </table>
            </div>
        </div>
        <div class="col-xs-6">
            <div class="info-card">
                <table>
                    <tr><td class="label">Student ID:</td><td class="val">{{ doc.student }}</td></tr>
                    <tr><td class="label">Name:</td><td class="val">{{ doc.student_name }}</td></tr>
                </table>
            </div>
        </div>
    </div>

    <div class="amount-box">
        <p>Amount Received</p>
        <h2>{{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(doc.amount) }}</h2>
    </div>

    {% if doc.discount_amount or doc.tax_amount %}
    <div class="row">
        <div class="col-xs-12">
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                {% if doc.discount_amount %}
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">Discount Applied:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; color: #d32f2f;">
                        - {{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(doc.discount_amount) }}
                    </td>
                </tr>
                {% endif %}
                {% if doc.tax_amount %}
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">Tax (GST):</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">
                        + {{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(doc.tax_amount) }}
                    </td>
                </tr>
                {% endif %}
                {% if doc.discount_amount or doc.tax_amount %}
                <tr>
                    <td style="padding: 10px; font-weight: bold;">Grand Total:</td>
                    <td style="padding: 10px; text-align: right; font-weight: bold;">
                        {{ doc.currency or '₹' }} {{ frappe.utils.fmt_money(doc.grand_total) }}
                    </td>
                </tr>
                {% endif %}
            </table>
        </div>
    </div>
    {% endif %}

    <div class="footer-notes">
        <p>Thank you for your payment!</p>
        <p>This is a computer-generated receipt and does not require a signature.</p>
    </div>
</div>
"""

    if not frappe.db.exists("Print Format", "Fees Payment Receipt"):
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "name": "Fees Payment Receipt",
            "doc_type": "Fees Payment Entry",
            "module": "BB Academy",
            "custom_format": 1,
            "standard": "Yes",
            "print_format_builder": 0,
            "html": payment_html
        })
        doc.insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("Print Format", "Fees Payment Receipt")
        doc.html = payment_html
        doc.save(ignore_permissions=True)

    frappe.db.commit()

create_print_formats()
