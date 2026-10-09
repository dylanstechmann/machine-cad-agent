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
$taskCodexDirectory = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$taskConfigPath = Join-Path $taskCodexDirectory 'config.toml'
$taskConfigText = [IO.File]::ReadAllText($taskConfigPath)
$taskPattern = '(?ms)(^\[mcp_servers\.machine_cad_agent\]\r?\n)(.*?)(?=^\[|\z)'
$taskRegex = [regex]::new($taskPattern)
if (-not $taskRegex.IsMatch($taskConfigText)) { throw 'Could not find the registered server section.' }
$taskUpdated = $taskRegex.Replace($taskConfigText, [Text.RegularExpressions.MatchEvaluator]{
    param($taskMatch)
    $taskBody = $taskMatch.Groups[2].Value
    $taskOriginalBody = $taskBody
    if ($taskBody -notmatch '(?m)^startup_timeout_sec\s*=') { $taskBody += "`nstartup_timeout_sec = 30`n" }
    if ($taskBody -notmatch '(?m)^tool_timeout_sec\s*=') { $taskBody += "tool_timeout_sec = 180`n" }
    if ($taskBody -eq $taskOriginalBody) { return $taskMatch.Value }
    $taskMatch.Groups[1].Value + $taskBody + "`n"
}, 1)
if ($taskUpdated -ne $taskConfigText) {
    [IO.File]::WriteAllText($taskConfigPath, $taskUpdated, [Text.UTF8Encoding]::new($false))
}
Write-Output 'CAD MCP registered. Start a fresh Codex session in this project to load its tools.'
