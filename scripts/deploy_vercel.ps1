# Publica el proyecto en Vercel usando la API REST.
# Requiere un token en $env:VERCEL_TOKEN o una sesion previa de `vercel login`.
# Uso:
#   .\scripts\deploy_vercel.ps1
#   $env:VERCEL_TOKEN = '...'; .\scripts\deploy_vercel.ps1

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$team = 'team_NLcorVijJIMVIKkZJJAZ6cTP'
$projectName = 'simulador-ptar'

$token = $env:VERCEL_TOKEN
if (-not $token) {
    $authPath = Join-Path $env:APPDATA 'com.vercel.cli\Data\auth.json'
    if (-not (Test-Path $authPath)) {
        throw "No hay token. Define VERCEL_TOKEN o ejecuta 'vercel login' primero."
    }
    $token = (Get-Content $authPath -Raw | ConvertFrom-Json).token
}

$headers = @{ Authorization = "Bearer $token" }

function Call-Vercel {
    param([string]$Method, [string]$Path, $Body)
    $uri = "https://api.vercel.com$Path"
    if ($uri -match '\?') { $uri += "&teamId=$team" } else { $uri += "?teamId=$team" }
    $params = @{ Method = $Method; Uri = $uri; Headers = $headers; TimeoutSec = 120 }
    if ($null -ne $Body) {
        $json = $Body | ConvertTo-Json -Depth 20 -Compress
        $params.Body = [System.Text.Encoding]::UTF8.GetBytes($json)
        $params.ContentType = 'application/json; charset=utf-8'
    }
    return Invoke-RestMethod @params
}

$exclude = @(
    '^\.git/', '^\.vercel/', '^backend/\.venv/', '^backend/\.pytest_cache/',
    '^backend/tests/', '^frontend/node_modules/', '^frontend/dist/',
    '__pycache__/', '^docs/simulador-ptar-con-three-js\.json$', '\.pyc$'
)

$files = @()
Get-ChildItem -LiteralPath $root -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($root.Length + 1).Replace('\', '/')
    $skip = $false
    foreach ($pattern in $exclude) {
        if ($rel -match $pattern) { $skip = $true; break }
    }
    if (-not $skip) {
        $files += [pscustomobject]@{
            file = $rel
            data = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
        }
    }
}
Write-Host "Archivos: $($files.Count)"

try {
    $project = Call-Vercel 'GET' "/v9/projects/$projectName" $null
    Write-Host "Proyecto: $($project.id)"
}
catch {
    $project = Call-Vercel 'POST' '/v11/projects' @{ name = $projectName; framework = 'fastapi' }
    Write-Host "Proyecto creado: $($project.id)"
}

$deployment = Call-Vercel 'POST' '/v13/deployments' @{
    name = $projectName
    project = $projectName
    target = 'production'
    files = $files
    projectSettings = @{ framework = 'fastapi' }
}
Write-Host "Despliegue: $($deployment.id)"

for ($i = 1; $i -le 90; $i++) {
    Start-Sleep -Seconds 10
    $state = Call-Vercel 'GET' "/v13/deployments/$($deployment.id)" $null
    Write-Host ("[{0,4}s] {1}" -f ($i * 10), $state.readyState)
    if ($state.readyState -in @('READY', 'ERROR', 'CANCELED')) { break }
}

$final = Call-Vercel 'GET' "/v13/deployments/$($deployment.id)" $null
Write-Host "Estado: $($final.readyState)"
Write-Host "URL: https://$($final.url)"
if ($final.alias) { Write-Host "Alias: $($final.alias -join ', ')" }
if ($final.errorMessage) { Write-Host "Error: $($final.errorMessage)" }
