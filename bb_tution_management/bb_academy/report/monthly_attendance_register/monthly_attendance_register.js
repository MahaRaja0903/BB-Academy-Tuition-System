
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
        // Freeze Sr No / Student ID / Student Name columns.
        setTimeout(function() {
            var wrapper = (datatable && datatable.wrapper) || document.querySelector('.report-wrapper .datatable');
            if (!wrapper) return;

            // Scope every rule below to this report only, so other datatables
            // (list views, other reports) are never touched.
            wrapper.classList.add('mar-freeze');
            var page = wrapper.closest('.page-container') || wrapper.closest('.page-body');
            if (page) page.classList.add('mar-page');

            var style = document.getElementById('monthly-attendance-freeze-cols');
            if (!style) {
                style = document.createElement('style');
                style.id = 'monthly-attendance-freeze-cols';
                document.head.appendChild(style);
            }

            // Measure from the natural (unstuck, unscrolled) layout, otherwise the
            // offsets from the previous render skew the new ones.
            style.textContent = '';
            var scrollable = wrapper.querySelector('.dt-scrollable');
            var prevScroll = scrollable ? scrollable.scrollLeft : 0;
            if (scrollable) scrollable.scrollLeft = 0;

            // Header and body cells are sized by separate rules in frappe-datatable
            // (.dt-cell__content--header-N vs .dt-cell__content--col-N) and can differ
            // by a pixel or two, so measure each row on its own instead of assuming
            // they line up.
            function offsetsOf(row, headerRow) {
                if (!row) return null;
                var rowLeft = row.getBoundingClientRect().left;
                var out = [];
                for (var i = 0; i < 3; i++) {
                    var sel = headerRow ? '.dt-cell--header-' + i : '.dt-cell--col-' + i;
                    var cell = row.querySelector(sel);
                    if (!cell) return null;
                    out.push(cell.getBoundingClientRect().left - rowLeft);
                }
                return out;
            }

            var bodyOffsets = offsetsOf(wrapper.querySelector('.dt-scrollable .dt-row'), false);
            var headOffsets = offsetsOf(wrapper.querySelector('.dt-header .dt-row'), true);

            // Fall back to whichever measurement succeeded rather than to guessed widths.
            bodyOffsets = bodyOffsets || headOffsets;
            headOffsets = headOffsets || bodyOffsets;
            if (!bodyOffsets) return;

            // .dt-cell--col-N is on header, filter and body cells alike, so the
            // filter row stays pinned with the header it belongs to.
            function rules(scope, offsets, zIndex) {
                return offsets.map(function(left, i) {
                    return '.mar-freeze ' + scope + ' .dt-cell--col-' + i + ' {' +
                        'position: sticky !important;' +
                        'left: ' + left + 'px !important;' +
                        'z-index: ' + zIndex + ' !important;' +
                        'background-color: var(--fg-color, #fff) !important;' +
                    '}';
                }).join('\n');
            }

            style.textContent = `
                /* Contain the sticky z-indexes in their own stacking context so
                   frozen columns/header can never cover the filter dropdowns. */
                .mar-freeze {
                    position: relative;
                    z-index: 0;
                }
                /* Keep the filter row (and its Link/Select dropdowns) on top. */
                .mar-page .page-form,
                .mar-page .filter-section,
                .mar-page .standard-filter-section {
                    position: relative;
                    z-index: 10;
                }
                .mar-page .awesomplete > ul,
                .mar-page .filter-popover,
                .mar-page .dropdown-menu {
                    z-index: 1050 !important;
                }
                .mar-freeze .dt-scrollable {
                    overflow-x: auto !important;
                }
                ${rules('.dt-scrollable', bodyOffsets, 2)}
                ${rules('.dt-header', headOffsets, 3)}
                /* Edge of the frozen block, so scrolled-under days read as hidden
                   rather than clipped. */
                .mar-freeze .dt-scrollable .dt-cell--col-2,
                .mar-freeze .dt-header .dt-cell--col-2 {
                    box-shadow: 1px 0 0 0 var(--dark-border-color, #d1d8dd);
                }
                /* Keep header row sticky on vertical scroll */
                .mar-freeze .dt-header {
                    position: sticky !important;
                    top: 0 !important;
                    z-index: 4 !important;
                }
            `;

            if (scrollable) scrollable.scrollLeft = prevScroll;
        }, 200);
    }
};
