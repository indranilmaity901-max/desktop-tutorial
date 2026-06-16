param(
  [Parameter(Mandatory=$true)][string]$PythonExe,
  [Parameter(Mandatory=$true)][string]$RepoPath
)

$agentPath = Join-Path $RepoPath "agent-desktop"
$action = New-ScheduledTaskAction -Execute $PythonExe -Argument "-m windows_agent.main" -WorkingDirectory $agentPath
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "WPACS Desktop Agent" -Action $action -Trigger $trigger -Description "Runs the WPACS Windows Desktop Agent at user logon."
