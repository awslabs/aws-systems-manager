#
# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

$ErrorActionPreference = 'stop'
$ProgressPreference = 'silentlycontinue'
$VerbosePreference = 'continue'
 
$WorkDir = 'c:\Amazon'
if (!(Test-Path -Path $WorkDir)) {
    mkdir -Path $WorkDir
}
Set-Location -Path c:\Amazon
 
function Write-Log {
  [CmdletBinding()]
  param (
    [Parameter(Mandatory = $true)]
    [string] $Message
  )
  Add-Content -Path $env:SystemDrive\Win32-OpenSSH.log -Value ('{0}: {1}' -f (Get-Date -Format o), $Message)
}
 
function Install-PowerShellCore {
    Write-Log -Message 'Installing PowerShell Core'
    $SourceURL = 'https://github.com/PowerShell/PowerShell/releases/download/v6.0.0/PowerShell-6.0.0-win-x64.zip'
    $UnzipFolder = '{0}\pwsh' -f $env:SystemDrive
    $TargetFile = '{0}\pwsh.zip' -f $UnzipFolder
 
    if (Get-Command -Name pwsh.exe -ErrorAction Ignore) {
        Write-Log -Message 'Skipping install of PowerShell Core. Already present.'
        return
    }
    
    mkdir -Path $UnzipFolder -ErrorAction Ignore
    Invoke-WebRequest -OutFile $TargetFile -Uri $SourceURL
    Expand-Archive -Path $TargetFile -DestinationPath $UnzipFolder -Force
    Remove-Item -Path $TargetFile
    [System.Environment]::SetEnvironmentVariable('PATH', ($env:PATH += (';{0}' -f $UnzipFolder)), [System.EnvironmentVariableTarget]::Machine)
    Write-Log -Message 'Finished installing PowerShell Core'
}
 
function Install-PuTTY {
  if (Get-Command -Name putty.exe -ErrorAction Ignore) {
    Write-Log -Message 'Skipping install of PuTTY. Already installed.'
    return
  }
 
  Write-Log -Message 'Installing PuTTY'
  $PuTTYURL = 'https://the.earth.li/~sgtatham/putty/latest/w64/putty-64bit-0.70-installer.msi'
  $ZipFile = '{0}\putty.msi' -f $pwd
  Invoke-WebRequest -Uri $PuTTYURL -OutFile $ZipFile
  msiexec /package "$ZipFile" /passive /norestart
  Remove-Item -Path $ZipFile
  Write-Log -Message 'Finished installing PuTTY'
}
 
 
function Install-OpenSSH {
    ## https://github.com/PowerShell/Win32-OpenSSH/wiki/Install-Win32-OpenSSH
 
    $OpenSSHSourceURL = 'https://github.com/PowerShell/Win32-OpenSSH/releases/download/v1.0.0.0/OpenSSH-Win64.zip'
    $OpenSSHZip = '{0}\OpenSSH-Win64.zip' -f $env:TEMP
    $TargetPath = '{0}\OpenSSH' -f $env:ProgramFiles
 
    Invoke-WebRequest -OutFile $OpenSSHZip -Uri $OpenSSHSourceURL
    Unblock-File -Path $OpenSSHZip
    Expand-Archive -Path $OpenSSHZip -DestinationPath $env:ProgramFiles -Force
    Remove-Item -Path $OpenSSHZip -Force
 
    Rename-Item -Path ('{0}-Win64' -f $TargetPath) -NewName $TargetPath -Force -ErrorAction Ignore
 
    Set-Location -Path $TargetPath
 
    powershell -ExecutionPolicy Bypass -File ('{0}\install-sshd.ps1' -f $TargetPath)
    Write-Log -Message 'Installed SSHD'
 
    ### Fix file permissions for host keys
    & ./FixHostFilePermissions.ps1 -Confirm:$false
    
    ### Create registry configuration for SSH default shell
    New-Item -Path HKLM:\Software\OpenSSH -ErrorAction Ignore
    Set-ItemProperty -Path HKLM:\SOFTWARE\OpenSSH -Name DefaultShell -Value c:\pwsh\pwsh.exe
    #Set-ItemProperty -Path HKLM:\SOFTWARE\OpenSSH -Name DefaultShellCommandOption -Value '-Command'
}
 
function Complete-SSHDConfig {
  Write-Log -Message 'Configuring SSH daemon'
 
  $ConfigPath = '{0}\ssh\sshd_config' -f $env:ProgramData
    
  ### Generate a Certificate Authority key to sign user public keys with
  ./ssh-keygen -t rsa -f ca_userkeys -q -N '""'    
  Add-Content -Path $ConfigPath -Value "`r`n",'TrustedUserCAKeys ca_userkeys.pub', 'PubkeyAuthentication yes'
  Write-Log -Message 'Finished generating Certificate Authority signing key'
  
  Add-Content -Path $ConfigPath -Value '','Subsystem powershell c:/pwsh/pwsh.exe -sshs -NoLogo -NoProfile'
  $NewConfig = Get-Content -Path $ConfigPath | ForEach-Object -Process {
    $PSItem -replace '^.*PasswordAuthentication.*$', 'PasswordAuthentication No'
  }
  Set-Content -Path $ConfigPath -Value $NewConfig
  Write-Log -Message 'Finished configuring SSH daemon'
}
 
function Build-SSHDAuthorizedKeys {
  <#
  .Parameter ParameterName
  The name of the AWS Systems Manager parameter that contains your SSH public key.
  #>
  [CmdletBinding()]
  param (
  )
 
  Write-Log -Message 'Configuring authorized_keys file'
  $ProfilePath = '{0}\Users\Administrator\.ssh' -f $env:SystemDrive
  if (!(Test-Path -Path $ProfilePath)) {
    mkdir -Path $ProfilePath
  }
 
  # Write the user's public key into the Administrator account's profile 
  $PublicKey = Invoke-RestMethod -Uri http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key
  Set-Content -Path $ProfilePath\authorized_keys -Value $PublicKey
  Write-Log -Message 'Finished configuring authorized_keys file'
}
 
function StartServices {
  [CmdletBinding()]
  param ( )
 
  Write-Log -Message 'Configuring services for automatic startup'
  Set-Service sshd -StartupType Automatic -ErrorAction Ignore
  Set-Service ssh-agent -StartupType Automatic -ErrorAction Ignore
 
  Write-Log -Message 'Starting services'
  Start-Service -Name sshd
  Start-Service -Name ssh-agent
  Write-Log -Message 'Finished starting services'
}
 
function Set-OpenSSHFirewall {
  [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
  param (
    [switch] $Force
  )
  if ($PSCmdlet.ShouldProcess('Windows Firewall', 'Open SSH connectivity')) {
    if ($Force -or $PSCmdlet.ShouldContinue()) {
      Write-Log -Message 'Starting configuration of Windows Firewall rule for SSH daemon'
      New-NetFirewallRule -LocalPort 22 -Direction Inbound -Profile Any -DisplayName sshd22 -Name 'Secure Shell (SSH) Daemon (sshd)' -Enabled true -Action Allow -Protocol TCP -ErrorAction Ignore
      Write-Log -Message 'Configured the Windows Firewall for ssh daemon'
    }
  }
}
 
Install-PowerShellCore
Install-PuTTY
Install-OpenSSH
Complete-SSHDConfig
Build-SSHDAuthorizedKeys
StartServices
Set-OpenSSHFirewall