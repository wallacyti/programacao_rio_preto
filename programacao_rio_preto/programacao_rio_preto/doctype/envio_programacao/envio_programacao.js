// Formulário do card de programação (substitui o card do Pipefy).

const PRP_CORES = {
	"Aguardando Entrega": "red",
	"Aguardando Reenvio": "pink",
	"Programas Recebidos": "yellow",
	"Reedição": "orange",
	"Enviado para o VIZ One": "purple",
	"Enviado Programação": "blue",
	"Exibido": "green",
};

frappe.ui.form.on("Envio Programacao", {
	setup(frm) {
		frm.set_query("programa", () => ({ filters: { ativo: 1 } }));
		frm.set_query("cliente", () => ({ filters: { ativo: 1 } }));
	},

	refresh(frm) {
		if (frm.doc.etapa) {
			frm.page.set_indicator(__(frm.doc.etapa), PRP_CORES[frm.doc.etapa] || "gray");
		}
		prp_mostrar_prazo(frm);
		if (frm.doc.link_viz) {
			frm.add_custom_button(__("Abrir no VIZ"), () => window.open(frm.doc.link_viz, "_blank"));
		}
		if (!frm.is_new()) {
			prp_botoes_de_movimento(frm);
		}
	},

	recebido_com_erro(frm) {
		if (frm.doc.recebido_com_erro !== "Sim") return;
		frm.scroll_to_field("prob_video");
	},
});

function prp_tempo(minutos) {
	const m = Math.abs(Math.round(minutos));
	if (m < 60) return m === 1 ? "1 minuto" : `${m} minutos`;
	const h = Math.round(m / 60);
	if (h < 24) return h === 1 ? "1 hora" : `${h} horas`;
	const d = Math.round(h / 24);
	if (d < 45) return d === 1 ? "1 dia" : `${d} dias`;
	const meses = Math.round(d / 30);
	if (meses < 12) return meses === 1 ? "1 mês" : `${meses} meses`;
	const anos = Math.round(d / 365);
	return anos === 1 ? "1 ano" : `${anos} anos`;
}

function prp_mostrar_prazo(frm) {
	if (!frm.doc.data_hora_exibicao || frm.doc.etapa === "Exibido") return;
	const minutos = moment(frm.doc.data_hora_exibicao).diff(moment(), "minutes");
	const quando = frappe.datetime.str_to_user(frm.doc.data_hora_exibicao);
	if (minutos < 0) {
		frm.dashboard.set_headline_alert(
			`<span class="indicator-pill red">${__("Exibição vencida")}</span>&nbsp; ${quando} · há ${prp_tempo(minutos)}`
		);
	} else {
		frm.dashboard.set_headline_alert(
			`<span class="indicator-pill blue">${__("Exibição")}</span>&nbsp; ${quando} · em ${prp_tempo(minutos)}`
		);
	}
}

function prp_botoes_de_movimento(frm) {
	frappe.call({
		method: "programacao_rio_preto.fluxo.opcoes_de_movimento",
		args: { name: frm.doc.name },
		callback(r) {
			(r.message || []).forEach((op) => {
				const rotulo = (op.volta ? "← " : "→ ") + __(op.etapa);
				frm.add_custom_button(rotulo, () => prp_mover(frm, op), __("Mover para"));
			});
		},
	});
}

async function prp_mover(frm, op) {
	if (frm.is_dirty()) {
		await frm.save();
	}
	frappe.call({
		method: "programacao_rio_preto.fluxo.mover",
		args: { name: frm.doc.name, etapa: op.etapa },
		freeze: true,
		freeze_message: __("Movendo para {0}...", [__(op.etapa)]),
		callback() {
			frappe.show_alert({ message: __("Movido para {0}", [__(op.etapa)]), indicator: "green" });
			frm.reload_doc();
		},
	});
}
