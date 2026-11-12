# Instala (ou atualiza) o app programacao_rio_preto no Docker local (site helpdesk.localhost).
#
# Uso (PowerShell):
#   powershell -ExecutionPolicy Bypass -File "<pasta>\frappe-dev\apps\programacao_rio_preto\tools\instalar-dev.ps1"
#
# Pode rodar quantas vezes quiser: na primeira instala, depois so aplica as mudancas (migrate).
# So mexe no ambiente local.
$ErrorActionPreference = "Continue"
$FrappeDev = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$Bench = "/home/frappe/benches/frappe-bench"
$Site = "helpdesk.localhost"
$App = "programacao_rio_preto"
$Url = "http://helpdesk.localhost:8000"
$Log = Join-Path $FrappeDev "instalar-programacao.log"
Start-Transcript -Path $Log -Force | Out-Null
trap { Write-Host "ERRO: $_" -ForegroundColor Red; Stop-Transcript | Out-Null; exit 1 }

function Passo($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Bench([string]$comando) {
    Write-Host "   $comando" -ForegroundColor DarkGray
    $saida = "/workspace/apps/programacao_rio_preto/tools/ultimo-comando.log"
    docker compose exec -T -w $Bench frappe bash -lc "set -o pipefail; ( $comando ) 2>&1 | tee $saida"
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $comando (saida em apps\programacao_rio_preto\tools\ultimo-comando.log)" }
}
function Esperar() {
    # O PowerShell nao resolve *.localhost; a checagem roda dentro do container.
    $teste = "import urllib.request as u; r=u.Request('http://127.0.0.1:8000/api/method/ping', headers={'Host': '$Site'}); print(u.urlopen(r, timeout=5).status)"
    $limite = (Get-Date).AddMinutes(8)
    do {
        $status = docker compose exec -T frappe python3 -c $teste 2>$null
        if ("$status".Trim() -eq "200") { return }
        Start-Sleep -Seconds 5
    } until ((Get-Date) -gt $limite)
    throw "O Frappe nao respondeu em 8 minutos. Veja: docker compose logs frappe --tail 80"
}

Passo "Verificando o Docker"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $exe = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $exe)) { throw "Docker Desktop nao encontrado. Abra-o manualmente e rode de novo." }
    Start-Process $exe
    $limite = (Get-Date).AddMinutes(3)
    do { Start-Sleep -Seconds 5; docker info *> $null } until ($LASTEXITCODE -eq 0 -or (Get-Date) -gt $limite)
    if ($LASTEXITCODE -ne 0) { throw "O Docker nao respondeu em 3 minutos." }
}

Set-Location $FrappeDev
Passo "Subindo os containers"
docker compose up -d
if ($LASTEXITCODE -ne 0) { throw "docker compose up falhou." }
Esperar

Passo "Ligando o app ao bench"
Bench "test -L apps/$App || ln -s /workspace/apps/$App apps/$App"
Bench "bench pip install --no-deps -e apps/$App"

Passo "Registrando o app no bench"
Bench "python3 /workspace/apps/$App/tools/registrar_app.py"

Passo "Backup do site antes de mexer"
Bench "bench --site $Site backup"


Passo "Instalando no site $Site"
$instalado = (docker compose exec -T -w $Bench frappe bash -lc "bench --site $Site list-apps") -match $App
if ($instalado) {
    Write-Host "   ja instalado: aplicando mudancas"
    Bench "bench --site $Site migrate"
} else {
    Bench "bench --site $Site install-app $App"
}
Bench "bench build --app $App"
Bench "bench --site $Site clear-cache"

Passo "Reiniciando o Frappe"
docker compose restart frappe
Esperar

Passo "Conferindo"
Bench "bench --site $Site list-apps"

Passo "Pronto"
Write-Host "Programacao Rio Preto: $Url/desk/programacao-rio-preto"
Write-Host "Kanban:                $Url/desk/envio-programacao/view/kanban/Programa%C3%A7%C3%A3o%20Rio%20Preto"
Start-Process "$Url/desk/programacao-rio-preto"
Write-Host "FIM-OK"
Stop-Transcript | Out-Null
