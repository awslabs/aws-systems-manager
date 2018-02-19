## Overview

This PowerShell script was developed with the intention of deploying it to Windows Server systems, through the `AWS-RunRemoteScript` AWS Systems Manager document. When executed, this PowerShell script will perform the following actions:

* Install PowerShell Core edition
* Install the Win32 OpenSSH daemon for Microsoft Windows
* Configure the Windows Firewall to allow inbound SSH connections
* Configure OpenSSH to use PowerShell Core as the default shell