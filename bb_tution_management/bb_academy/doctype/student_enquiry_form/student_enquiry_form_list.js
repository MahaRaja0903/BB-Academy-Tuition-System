frappe.listview_settings['Student Enquiry Form'] = {
	onload: function(listview) {
		let filter_field = listview.page.add_field({
			fieldname: 'mobile_number_search',
			label: __('Mobile Number Search'),
			fieldtype: 'Data',
			change: function() {
				listview.refresh();
			}
		});

		// Move the search field to the far left of the filter area
		if (filter_field.$wrapper) {
			listview.page.page_form.prepend(filter_field.$wrapper);
		}

		// Remove the custom field from get_filters_for_args so it doesn't crash get_count
		let original_get_filters = listview.get_filters_for_args;
		listview.get_filters_for_args = function() {
			let filters = original_get_filters.apply(listview, arguments);
			return filters.filter(f => f[1] !== 'mobile_number_search');
		};

		let original_get_args = listview.get_args;
		listview.get_args = function() {
			let args = original_get_args.apply(listview, arguments);
			let mobile_search = filter_field.get_value();
			
			if (mobile_search) {
				args.or_filters = [
					['father_number', 'like', '%' + mobile_search + '%'],
					['mother_number', 'like', '%' + mobile_search + '%']
				];
			}
			
			return args;
		};
        
        let original_get_count_str = listview.get_count_str;
        listview.get_count_str = function() {
            let filters = this.get_filters_for_args();
            let args = {
                doctype: this.doctype,
                filters: filters,
                limit: this.count_upper_bound
            };
            
            let mobile_search = filter_field.get_value();
            if (mobile_search) {
                args.or_filters = [
                    ['father_number', 'like', '%' + mobile_search + '%'],
                    ['mother_number', 'like', '%' + mobile_search + '%']
                ];
            }
            
            return frappe.call({
                method: 'frappe.desk.reportview.get_count',
                args: args
            }).then(r => {
                let total_count = r.message || 0;
                this.total_count = total_count;
                let count_str = total_count === this.count_upper_bound ? `${format_number(total_count - 1, null, 0)}+` : format_number(total_count, null, 0);
                this.get_count_element().html(count_str);
                return total_count;
            });
        };
	}
};
