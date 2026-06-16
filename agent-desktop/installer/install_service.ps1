param(
  [Parameter(Mandatory=$true)][string]$PythonExe,
  [Parameter(Mandatory=$true)][string]$RepoPath
)

$agentPath = Join-Path $RepoPath "agent-desktop"
Push-Location $agentPath
& $PythonExe -m windows_agent.service install --startup auto
& $PythonExe -m windows_agent.service start
Pop-Location
