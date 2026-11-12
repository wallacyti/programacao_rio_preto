"""Garante 'programacao_rio_preto' em sites/apps.txt, um app por linha (corrige nomes grudados)."""
from pathlib import Path

APP = "programacao_rio_preto"
arquivo = Path("sites/apps.txt")
texto = arquivo.read_text(encoding="utf-8")
# conserta o caso em que o app foi acrescentado sem quebra de linha (ex.: "telephonyprogramacao_rio_preto")
linhas = []
for linha in texto.split():
    if linha != APP and linha.endswith(APP):
        linhas += [linha[: -len(APP)], APP]
    else:
        linhas.append(linha)
if APP not in linhas:
    linhas.append(APP)
linhas = list(dict.fromkeys(l for l in linhas if l))
arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
print("apps.txt:", ", ".join(linhas))
