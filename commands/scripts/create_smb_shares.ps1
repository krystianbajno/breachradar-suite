param (
    [string]$ShareName,
    [string]$SharePath
)

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator."
    exit 1
}

if (-Not (Test-Path -Path $SharePath)) {
    Write-Host "Creating shared directory: $SharePath"
    New-Item -ItemType Directory -Force -Path $SharePath
}

$acl = Get-Acl $SharePath
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Everyone", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.SetAccessRule($rule)
Set-Acl -Path $SharePath -AclObject $acl

Write-Host "Creating SMB share: $ShareName"
New-SmbShare -Name $ShareName -Path $SharePath -FullAccess Everyone

Write-Host "SMB share $ShareName has been created and configured at $SharePath."

.\create_smb_share.ps1 -ShareName "MyShare" -SharePath "C:\SharedDirectory"