import frappe

def run():
    frappe.init(site="bbacademy.dreamtechsolution.com")
    frappe.connect()
    
    tables = frappe.db.sql("show tables", as_list=True)
    for table in tables:
        table_name = table[0]
        # Skip docfield and series etc.
        if not table_name.startswith("tab"): continue
        
        try:
            # Check all text/varchar fields
            columns = frappe.db.sql(f"DESCRIBE `{table_name}`", as_dict=True)
            text_columns = [c.Field for c in columns if 'varchar' in c.Type.lower() or 'text' in c.Type.lower() or 'data' in c.Type.lower()]
            if not text_columns: continue
            
            where_clauses = [f"`{col}` LIKE '%BB SMS Settings%'" for col in text_columns]
            query = f"SELECT name FROM `{table_name}` WHERE {' OR '.join(where_clauses)} LIMIT 1"
            
            res = frappe.db.sql(query)
            if res:
                print(f"FOUND IN TABLE: {table_name}")
                print(f"QUERY: {query}")
                print(f"RESULT: {res}")
        except Exception as e:
            pass
