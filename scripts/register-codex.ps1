$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskCompose = Join-Path $taskRoot 'compose.yaml'
$taskName = 'machine_cad_agent'
$taskArgs = @('compose', '--project-directory', $taskRoot, '-f', $taskCompose,
              'run', '--rm', '-T', 'dev', 'python', '-m', 'machine_cad.mcp_server')
if (-not (Get-Command codex -ErrorAction SilentlyContinue)) { throw 'Codex CLI must be on PATH.' }
$taskServers = & codex mcp list --json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Could not read Codex MCP configuration.' }
$taskExisting = $taskServers | Where-Object name -eq $taskName
if ($taskExisting) {
    if ($taskExisting.transport.command -ne 'docker' -or
        ($taskExisting.transport.args -join [char]0) -ne ($taskArgs -join [char]0)) {
        throw 'machine_cad_agent already points to another checkout. Remove or rename that registration before registering this folder.'
    }
    Write-Output 'This project is already registered.'
} else {
    & codex mcp add $taskName -- docker @taskArgs
    if ($LASTEXITCODE -ne 0) { throw 'Could not register the CAD MCP server.' }
}
Write-Output 'CAD MCP registered. Start a fresh Codex session in this project to load its tools.'
