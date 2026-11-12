# Programação Rio Preto — leia primeiro

App Frappe que substitui o pipe **PROGRAMAÇÃO_RIO PRETO** do Pipefy.
Testado em **Frappe 16.52.0** (mesma versão do Docker local e da produção) em 12/11/2026:
instalação limpa, 11 testes automáticos do fluxo, relatório e importador.

## 1. Instalar no Docker local

1. Copie a pasta `programacao_rio_preto` para `frappe-dev\apps\` (ao lado de `chamados_ti`).
2. Entre no container do bench e rode, dentro de `frappe-bench`:

```bash
# instala o pacote Python do app
uv pip install -e apps/programacao_rio_preto --python env/bin/python
#   (se o seu bench não usa uv: ./env/bin/pip install -e apps/programacao_rio_preto)

# registra o app no bench
grep -q programacao_rio_preto sites/apps.txt || echo programacao_rio_preto >> sites/apps.txt

# instala no site (mesmo site do Helpdesk, como será na produção)
bench --site helpdesk.localhost install-app programacao_rio_preto
bench build --app programacao_rio_preto
bench --site helpdesk.localhost clear-cache
```

3. Reinicie o bench (ou o container) e acesse **/desk/programacao-rio-preto** (o endereço /app/... redireciona para lá).

A instalação cria:
- os papéis **Programação RP - Usuário** e **Programação RP - Gestor**;
- o Kanban **Programação Rio Preto** com as 7 fases, nas cores do Pipefy;
- um contador por fase na área de trabalho;
- 26 clientes e 218 programas vistos nos prints (a lista completa vem do importador).

4. Dê o papel aos usuários: **Usuário → Funções** → *Programação RP - Usuário* (ou *Gestor*).

> Não há colisão de nomes com o Helpdesk nem com o `inbrac_processos`: todos os DocTypes
> são novos (`Envio Programacao`, `Envio Programacao Etapa`, `Programa TV`, `Cliente Programacao`).
> Mesmo assim, confira na produção antes: `select name from tabDocType where name in
> ('Envio Programacao','Envio Programacao Etapa','Programa TV','Cliente Programacao');`

## 2. Como o Pipefy foi reproduzido

| Pipefy | Frappe |
|---|---|
| Card | **Envio Programacao** (`PRP-AAAA-#####`), título = nome do programa |
| Formulário inicial | Seção "Formulário inicial" + "Material" do mesmo formulário |
| Fases (7 colunas) | Campo **Etapa** + Kanban "Programação Rio Preto" |
| Mover card para fase | Botão **Mover para ▸** no formulário ou arrastar no Kanban |
| Formulário de fase | Seções "Conferência do recebimento", "Conferência no Master" e "Exibição", que aparecem na fase certa |
| Campo obrigatório da fase | Validado ao sair da fase (vale para botão **e** para o Kanban) |
| Histórico | Tabela **Histórico de etapas**: entrada, saída, tempo, quem moveu e as respostas da conferência |
| Atividades | Linha do tempo nativa (toda alteração de campo fica registrada) |
| Responsável | **Atribuir a** (barra lateral) |
| Etiquetas (AO VIVO, PROGRAMADO NO MASTER) | **Tags** nativas (barra lateral; aparecem no card do Kanban) |
| Anexos / Comentários / Email / PDF | Nativos do Frappe (barra lateral, rodapé, menu ⋯ e Imprimir) |
| Vencimento | Data e hora da exibição: alerta no topo do card e data em vermelho na lista quando vencida |
| Procurar cards / filtros | Busca e filtros da lista (cliente, programa, etapa, filtro data, AO VIVO, REPRISE, erros) |
| Relatórios | Relatório **Ocorrências** (erros de recebimento, Master e exibição) + Report View da lista |
| Lista de clientes e de programas | Cadastros **Cliente Programacao** e **Programa TV**, com "Ativo" para aposentar sem apagar |

## 3. Regras de fase

Todas ficam em `programacao_rio_preto/fluxo.py`, num lugar só. Mudar o fluxo = editar esse arquivo.

| De | Para | Exige | Origem |
|---|---|---|---|
| Aguardando Entrega | Programas Recebidos | — | print |
| Aguardando Entrega | Enviado Programação | AO VIVO marcado | **hipótese** |
| Aguardando Reenvio | Programas Recebidos | — | **hipótese** |
| Programas Recebidos | Enviado para o VIZ One | conferência respondida; se "Sim", problema + ação (e ação ≠ devolvido) | print (+ hipótese no "Sim") |
| Programas Recebidos | Aguardando Reenvio | ação = Devolvido para o cliente reenviar | **hipótese** |
| Programas Recebidos | Reedição | ação = Corrigido em Rio Preto | **hipótese** |
| Programas Recebidos | Aguardando Entrega | — (voltar) | print |
| Reedição | Enviado para o VIZ One / Enviado Programação | — | **hipótese** |
| Enviado para o VIZ One | Enviado Programação / Programas Recebidos | — | **hipótese** |
| Enviado Programação | Exibido | conferência no Master respondida | print |
| Enviado Programação | Reedição | — (voltar) | print |
| Exibido | Enviado Programação | — (voltar) | print |

Todo card novo nasce em **Aguardando Entrega**.

## 4. Importar do Pipefy

No Pipefy: **Relatórios** → relatório com *todas as fases* e *todos os campos* (inclua ID, Fase atual,
Criado por, Criado em e Etiquetas) → **Exportar → Excel**. Copie o arquivo para dentro do container.

```bash
# 1) simular (não grava nada) — mostra contagem por fase, clientes/programas novos e avisos
bench --site helpdesk.localhost execute programacao_rio_preto.importador.importar \
  --kwargs "{'arquivo': '/caminho/export.xlsx', 'simular': 1}"

# 2) importar de verdade
bench --site helpdesk.localhost execute programacao_rio_preto.importador.importar \
  --kwargs "{'arquivo': '/caminho/export.xlsx', 'simular': 0}"
```

Opções: `'incluir_exibidos': 0` (pula os ~42 mil exibidos), `'exibidos_desde': '2026-01-01'`,
`'limite': 100` (teste). Pode rodar de novo: cards com o mesmo ID do Pipefy são pulados.

## 5. Testes automáticos

```bash
bench --site helpdesk.localhost set-config allow_tests true
bench --site helpdesk.localhost run-tests --app programacao_rio_preto
```

## 6. Pendências (confirmar com a equipe)

1. **As três empresas**: quem são e se precisam de separação de visão/permissão. Hoje todos veem tudo, como no Pipefy.
2. **Link do VIZ**: criei o campo "Link do material no VIZ" (pedido no briefing). No Pipefy não havia campo; confirmar onde ficava.
3. **Fases sem print** (Aguardando Reenvio, Reedição, Enviado para o VIZ One): campos e caminhos são hipóteses (tabela acima).
4. **Automações do Pipefy**: não vistas; podem existir regras que movem cards ou enviam e-mail.
5. **Obrigatórios**: deixei Cliente, Programa e Data/hora obrigatórios na criação (no Pipefy nada era obrigatório). Para voltar como era, desmarque "Obrigatório" via Personalizar Formulário.
6. **Filtro data**: agora é preenchido sozinho com a data da exibição (no Pipefy era digitado).
7. **Cadastro de programas**: só o Gestor cria/edita programas e clientes. Ajustável nas permissões.
8. **Cards antigos**: 556 em Aguardando Entrega e cards de 2025 em Enviado Programação — decidir o que importar.
