
frappe.query_reports["Monthly Attendance Register"] = {
    "filters": [
        {"fieldname":"from_date", "label":"From Date", "fieldtype":"Date", "default": frappe.datetime.month_start(), "reqd": 1},
        {"fieldname":"to_date", "label":"To Date", "fieldtype":"Date", "default": frappe.datetime.month_end(), "reqd": 1},
        {"fieldname":"standard", "label":"Standard", "fieldtype":"Link", "options":"Standard"},
        {"fieldname":"batch", "label":"Batch", "fieldtype":"Link", "options":"Batch"},
        {"fieldname":"gender", "label":"Gender", "fieldtype":"Select", "options":"\nBoys\nGirls"},
        {"fieldname":"late_days", "label":"Min Late Days", "fieldtype":"Int"},
        {"fieldname":"absent_days", "label":"Min Absent Days", "fieldtype":"Int"}
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname && column.fieldname.startsWith("day_") && value) {
            if (value === "P") {
                value = "<span style='color: green; font-weight: bold;'>P</span>";
            } else if (value === "A") {
                value = "<span style='color: red; font-weight: bold;'>A</span>";
            } else if (value === "L") {
                value = "<span style='color: orange; font-weight: bold;'>L</span>";
            } else if (value === "H") {
                value = "<span style='color: blue; font-weight: bold;'>H</span>";
            }
        }
        return value;
    },
    "after_datatable_render": function(datatable) {
        // Dynamically freeze Student ID and Student Name columns
        setTimeout(function() {
            // Find the actual widths of frozen columns by reading header cells
            var headerCells = document.querySelectorAll('.dt-header-cell');
            var colWidths = {};
            headerCells.forEach(function(cell) {
                var idx = cell.getAttribute('data-col-index');
                colWidths[idx] = cell.offsetWidth;
            });

            // col 0 = Sr No (row number), col 1 = Student ID, col 2 = Student Name
            var col0Width = colWidths['0'] || 60;
            var col1Width = colWidths['1'] || 120;
            var col1Left = col0Width;
            var col2Left = col0Width + col1Width;

            var style = document.getElementById('monthly-attendance-freeze-cols');
            if (!style) {
                style = document.createElement('style');
                style.id = 'monthly-attendance-freeze-cols';
                document.head.appendChild(style);
            }

            style.textContent = `
                .dt-scrollable {
                    overflow-x: auto !important;
                }
                /* Freeze Sr No column */
                .dt-cell[data-col-index="0"],
                .dt-header-cell[data-col-index="0"] {
                    position: sticky !important;
                    left: 0px !important;
                    z-index: 2 !important;
                    background-color: var(--fg-color, #fff) !important;
                }
                /* Freeze Student ID column */
                .dt-cell[data-col-index="1"],
                .dt-header-cell[data-col-index="1"] {
                    position: sticky !important;
                    left: ${col0Width}px !important;
                    z-index: 2 !important;
                    background-color: var(--fg-color, #fff) !important;
                }
                /* Freeze Student Name column */
                .dt-cell[data-col-index="2"],
                .dt-header-cell[data-col-index="2"] {
                    position: sticky !important;
                    left: ${col0Width + col1Width}px !important;
                    z-index: 2 !important;
                    background-color: var(--fg-color, #fff) !important;
                }
                /* Headers get higher z-index */
                .dt-header-cell[data-col-index="0"],
                .dt-header-cell[data-col-index="1"],
                .dt-header-cell[data-col-index="2"] {
                    z-index: 3 !important;
                }
                /* Keep header row sticky on vertical scroll */
                .dt-header {
                    position: sticky !important;
                    top: 0 !important;
                    z-index: 4 !important;
                }
            `;
        }, 200);
    }
};
