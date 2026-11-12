// Lista de envios: cor por etapa e destaque para exibição vencida.

frappe.listview_settings["Envio Programacao"] = {
	add_fields: ["etapa", "data_hora_exibicao", "ao_vivo", "reprise"],
	hide_name_column: true,

	get_indicator(doc) {
		const cores = {
			"Aguardando Entrega": "red",
			"Aguardando Reenvio": "pink",
			"Programas Recebidos": "yellow",
			"Reedição": "orange",
			"Enviado para o VIZ One": "purple",
			"Enviado Programação": "blue",
			"Exibido": "green",
		};
		return [__(doc.etapa), cores[doc.etapa] || "gray", "etapa,=," + doc.etapa];
	},

	formatters: {
		data_hora_exibicao(value, df, doc) {
			if (!value) return "";
			const texto = frappe.datetime.str_to_user(value);
			const vencido = doc.etapa !== "Exibido" && moment(value).isBefore(moment());
			return vencido ? `<span class="text-danger">${texto}</span>` : texto;
		},
	},

	onload(listview) {
		listview.page.add_inner_button(__("Kanban"), () => {
			frappe.set_route("List", "Envio Programacao", "Kanban", "Programação Rio Preto");
		});
	},
};
