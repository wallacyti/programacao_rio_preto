frappe.query_reports["Ocorrencias Programacao"] = {
	filters: [
		{ fieldname: "de", label: __("Exibição de"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -1) },
		{ fieldname: "ate", label: __("Exibição até"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "cliente", label: __("Cliente"), fieldtype: "Link", options: "Cliente Programacao" },
		{ fieldname: "programa", label: __("Programa"), fieldtype: "Link", options: "Programa TV" },
		{
			fieldname: "tipo",
			label: __("Tipo de ocorrência"),
			fieldtype: "Select",
			options: ["", "Recebimento", "Master", "Exibição"],
		},
	],
};
