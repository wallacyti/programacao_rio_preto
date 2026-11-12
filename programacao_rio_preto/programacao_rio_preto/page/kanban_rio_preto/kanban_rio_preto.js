// Atalho da barra lateral para o Kanban, na mesma guia.
// (Itens do tipo "URL" da barra lateral sempre abrem em nova guia no Frappe 16.)
// A página substitui a si mesma no histórico, para o botão Voltar não cair aqui de novo.
const PRP_KANBAN = "Programação Rio Preto";

function prp_corrigir_endereco() {
	// O desk pode regravar o endereço do atalho depois da troca de rota; ajusta a barra de endereço.
	const atalho = "/kanban-rio-preto";
	if (window.location.pathname.endsWith(atalho)) {
		const novo = window.location.pathname.slice(0, -atalho.length) +
			"/envio-programacao/view/kanban/" + encodeURIComponent(PRP_KANBAN);
		history.replaceState(history.state, "", novo);
	}
}

function prp_abrir_kanban() {
	frappe.route_flags.replace_route = true;
	Promise.resolve(frappe.set_route("List", "Envio Programacao", "Kanban", PRP_KANBAN)).then(() => {
		setTimeout(prp_corrigir_endereco, 50);
		setTimeout(prp_corrigir_endereco, 500);
	});
}

frappe.pages["kanban-rio-preto"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Kanban"), single_column: true });
};

frappe.pages["kanban-rio-preto"].on_page_show = function () {
	// espera o roteador terminar de mostrar esta página antes de trocar de rota
	setTimeout(() => {
		if (frappe.get_route_str() === "kanban-rio-preto") prp_abrir_kanban();
	}, 0);
};
