param(
    [string]$Command = 'demo',
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$CadArgs
)
$ErrorActionPreference = 'Stop'
$taskCompose = Join-Path $PSScriptRoot 'compose.yaml'
function Invoke-CadDocker {
    & docker compose --project-directory $PSScriptRoot -f $taskCompose @args
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed with exit code $LASTEXITCODE" }
}
if ($Command -eq 'demo') {
    Invoke-CadDocker build dev
    Invoke-CadDocker run --rm dev python -m machine_cad demo
    Invoke-CadDocker up -d viewer
    Write-Output 'Viewer: http://127.0.0.1:8765'
} elseif ($Command -eq 'test') {
    Invoke-CadDocker run --rm dev python -m unittest discover -s tests -v
} elseif ($Command -eq 'stop') {
    Invoke-CadDocker stop viewer
} else {
    Invoke-CadDocker run --rm dev python -m machine_cad $Command @CadArgs
}
