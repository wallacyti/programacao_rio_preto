from frappe.model.document import Document


def _limpar(texto):
	return " ".join((texto or "").split())


class ClienteProgramacao(Document):
	def before_insert(self):
		self.nome = _limpar(self.nome)

	def validate(self):
		self.nome = _limpar(self.nome)
