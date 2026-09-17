param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9_-]{0,31}$')]
    [string]$Profile,
    [ValidateSet('setup', 'login', 'probe')]
    [string]$Action = 'login',
    [string]$ProfileRoot = (Join-Path $env:LOCALAPPDATA 'VideoPipeline\gemini-profiles')
)

$ErrorActionPreference = 'Stop'
$profilePath = Join-Path $ProfileRoot $Profile
$geminiPath = Join-Path $profilePath '.gemini'
$policyPath = Join-Path $geminiPath 'policies'
$workspacePath = Join-Path $profilePath 'workspace'

New-Item -ItemType Directory -Force -Path $policyPath, $workspacePath | Out-Null

$settingsPath = Join-Path $geminiPath 'settings.json'
if (-not (Test-Path -LiteralPath $settingsPath)) {
    $settings = @{
        security = @{ disableYoloMode = $true }
        tools = @{ core = @() }
        general = @{ defaultApprovalMode = 'default' }
    } | ConvertTo-Json -Depth 4
    Set-Content -LiteralPath $settingsPath -Value $settings -Encoding utf8
}

# JSON is selected only for headless pipeline calls. Keeping it as a profile
# default would make the bare `gemini` login command headless as well.
$existingSettings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
if ($existingSettings.PSObject.Properties.Name -contains 'output') {
    $existingSettings.PSObject.Properties.Remove('output')
    Set-Content -LiteralPath $settingsPath -Value ($existingSettings | ConvertTo-Json -Depth 20) -Encoding utf8
}

$policy = @'
[[rule]]
toolName = "*"
decision = "deny"
priority = 999
denyMessage = "Pipeline generation profiles cannot use tools."
'@
Set-Content -LiteralPath (Join-Path $policyPath 'pipeline-deny-all.toml') -Value $policy -Encoding utf8

$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $profilePath /inheritance:r /grant:r "${currentIdentity}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "ACL konnte für $profilePath nicht gesetzt werden." }

if ($Action -eq 'setup') {
    Write-Host "Profil '$Profile' sicher eingerichtet: $profilePath"
    exit 0
}

$env:GEMINI_CLI_HOME = $profilePath
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_APPLICATION_CREDENTIALS -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_CLOUD_PROJECT -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_CLOUD_PROJECT_ID -ErrorAction SilentlyContinue
Set-Location -LiteralPath $workspacePath

if ($Action -eq 'login') {
    Write-Host "Gemini-Profil '$Profile': Bitte 'Sign in with Google' wählen und dieses Konto anmelden."
    & gemini
    exit $LASTEXITCODE
}

'Antworte ausschließlich mit diesem JSON: {"status":"ok"}' | & gemini --output-format json
exit $LASTEXITCODE
