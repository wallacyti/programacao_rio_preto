app_name = "programacao_rio_preto"
app_title = "Programação Rio Preto"
app_publisher = "REDEVIDA"
app_description = "Controle do envio de VTs para programação e exibição (substitui o pipe PROGRAMAÇÃO_RIO PRETO do Pipefy)"
app_email = ""
app_license = "mit"
required_apps = ["frappe"]

add_to_apps_screen = [
	{
		"name": app_name,
		"logo": "/assets/programacao_rio_preto/logo.svg",
		"title": "Programação RP",
		"route": "/app/programacao-rio-preto",
		"has_permission": "programacao_rio_preto.instalacao.tem_acesso",
	}
]

after_install = "programacao_rio_preto.instalacao.after_install"
after_migrate = "programacao_rio_preto.instalacao.after_migrate"
