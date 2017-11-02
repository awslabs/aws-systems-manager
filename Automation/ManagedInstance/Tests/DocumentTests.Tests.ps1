$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$sut = (Split-Path -Leaf $MyInvocation.MyCommand.Path).Replace(".Tests.", ".")
. "$here/$sut"

#$VerbosePreference = 'Continue'
Import-Module -Name AWSPowerShell.NetCore
$script:ManagedInstanceProfileDoc = 'awstest-CreateManagedInstanceProfile'
$script:ManagedInstanceProfileDocPath = "$here/../Output/awstest-CreateManagedInstanceProfile.json"
$script:SecurityGroupDoc = 'awstest-CreateSecurityGroup'
$script:SecurityGroupDocPath = "$here/../Output/awstest-CreateSecurityGroup.json"
$script:ManagedInstanceWindowsDoc= 'awstest-CreateManagedInstanceWindows'
$script:ManagedInstanceWindowsDocPath = "$here/../Output/awstest-CreateManagedInstanceWindows.json"
$script:ManagedInstanceLinuxDoc = 'awstest-CreateManagedInstanceLinux'
$script:ManagedInstanceLinuxDocPath = "$here/../Output/awstest-CreateManagedInstanceLinux.json"
$script:LinuxAmiId = 'ami-6df1e514'
$script:WindowsAmiId = 'ami-c4ffe3bd'
Set-DefaultAWSRegion us-west-2

$script:Documents = @{
    $script:ManagedInstanceProfileDoc = $script:ManagedInstanceProfileDocPath;
    $script:SecurityGroupDoc = $script:SecurityGroupDocPath;
    $script:ManagedInstanceWindowsDoc = $script:ManagedInstanceWindowsDocPath;
    $script:ManagedInstanceLinuxDoc = $script:ManagedInstanceLinuxDocPath
}
function Delete-OneDocument {
    [CmdletBinding()]
    param(
        [string]
        $Name
    )
    Write-Verbose "Finding if Document $Name exists" 
    try {
        $doc = Get-SSMDocument -Name $Name
        Write-Verbose "Removing document $Name" 
        Remove-SSMDocument -Name $Name -Force
    }
    catch {
        Write-Verbose "Document $Name does not exist" 
        return        
    }
}
function Delete-Document {
    [CmdletBinding()]
    param()

    Delete-OneDocument -Name $script:ManagedInstanceWindowsDoc
    Delete-OneDocument -Name $script:ManagedInstanceLinuxDoc
    Delete-OneDocument -Name $script:SecurityGroupDoc
    Delete-OneDocument -Name $script:ManagedInstanceProfileDoc
}

function Start-DocumentExecution {
    [CmdletBinding()]

    param(
        [string]
        $DocumentName,

        [string]
        $RoleName,

        [string]
        $GroupName,

        [string]
        $AmiId,

        [string]
        $InstanceType,

        [string]
        $KeyPairName,

        [string]
        $Platform
    )

    if ($documentname -ieq $script:ManagedInstanceProfileDoc) {
        $ExecutionId = Start-SSMAutomationExecution -DocumentName $DocumentName -Parameter @{RoleName = $RoleName}
    }

    if ($documentname -ieq $script:SecurityGroupDoc) {
        $ExecutionId = Start-SSMAutomationExecution -DocumentName $DocumentName -Parameter @{GroupName = $GroupName; Platform=$Platform}
    }

    if ($documentname -ieq $script:ManagedInstanceLinuxDoc){
        $ExecutionId = Start-SSMAutomationExecution -DocumentName $DocumentName -Parameter @{RoleName = $RoleName; GroupName = $GroupName; AmiId = $AmiId; InstanceType = $InstanceType; KeyPairName = $KeyPairName}
    }

    if ($documentname -ieq $script:ManagedInstanceWindowsDoc){
        $ExecutionId = Start-SSMAutomationExecution -DocumentName $DocumentName -Parameter @{RoleName = $RoleName; GroupName = $GroupName; AmiId = $AmiId; InstanceType = $InstanceType; KeyPairName = $KeyPairName}
    }
    $ExecutionId
}

function Wait-DocumentExecution {
    [CmdletBinding()]
    param(
        [string]
        $ExecutionId
    )
    $count = 10
    Write-Progress -Activity "Automation Execution" -Status "Waiting for execution $ExecutionId" -PercentComplete $count
    do{
        if ($count -gt 90){
            $count = 10
        }
        else {
            $count +=1 
        }
        
        $status = Get-SSMAutomationExecution -AutomationExecutionId $ExecutionId
        Write-Progress -Activity "Automation Execution" -Status "Waiting for execution $ExecutionId" -PercentComplete $count
        sleep 1;
    }while(($status.AutomationExecutionStatus -eq 'Pending') -or ($status.AutomationExecutionStatus -eq 'InProgress'))

    Write-Progress -Activity "Automation Execution" -Status "Waiting for execution $ExecutionId" -PercentComplete 100

    return $status
}

function Test-DocumentExecution {
    [CmdletBinding()]

    param(
        [string]
        $DocumentName,

        [string]
        $RoleName,

        [string]
        $GroupName,

        [string]
        $AmiId,

        [string]
        $InstanceType,

        [string]
        $KeyPairName,

        [string]
        $Platform
    )

    $InstanceId = [string]::Empty
    try {

        # create test key pair if the parameter is specified
        if ($PSBoundParameters.ContainsKey('KeyPairName'))
        {
            New-EC2KeyPair -KeyName $KeyPairName -Force
        }
        $ExecutionId = Start-DocumentExecution -DocumentName $DocumentName -RoleName $Rolename -GroupName $GroupName -Platform $Platform -AmiId $AmiId -InstanceType $InstanceType -KeyPairName $KeyPairName

        It "StartAutomation succeeded on $DocumentName" {
            $ExecutionId | should not be [string]::empty
        }

        It "Final status of $DocumentName" {
            $status = Wait-DocumentExecution -ExecutionId $ExecutionId
            $status.AutomationExecutionStatus | should be 'Success'
        }

        if ($PSBoundParameters.ContainsKey('RoleName')) 
        {
            for($count=10; $count -le 100; $count+=10)
            {
                Write-Progress -Activity 'IAM Refresh' -Status 'Waiting for IAM cache to update' -PercentComplete $count
                Start-Sleep -Milliseconds 300
            }
            It "Role $Rolename is created" {
                Get-IAMRole -RoleName $RoleName | should not be $null
            }

            It "Role policies for $RoleName" {
                Get-IAMAttachedRolePolicies -RoleName $Rolename | foreach PolicyName | should be 'AmazonEC2RoleforSSM'
            }

            $InstanceProfile = Get-IAMInstanceProfileForRole -RoleName $RoleName

            It "Role created with instance profile for $RoleName" {
                $InstanceProfile | should not be $null
            }

            It "Instance profile name for $RoleName is $RoleName" {
                $InstanceProfile.InstanceProfileName | Should be $RoleName
            }
        }

        if ($PSBoundParameters.ContainsKey('GroupName'))
        {
            for($count=10; $count -le 100; $count+=10)
            {
                Write-Progress -Activity 'Security Group Refresh' -Status 'Waiting for Security Group cache to update' -PercentComplete $count
                Start-Sleep -Milliseconds 300
            }

            $Group = Get-EC2SecurityGroup -GroupName $GroupName
            It "Group $GroupName is created" {
                $Group | should not be $null
            }

            if ($Platform -ieq 'Windows')
            {
                It "Number of ports open on Windows" {
                    $Group.IpPermissions.Count | Should be 1
                }

                It "RDP is allowed on Windows" {
                    $Group.IpPermissions | foreach FromPort | Should be 3389
                }
            }
            else {
                It "Number of ports open on Linux" {
                    $Group.IpPermissions.Count | Should be 1
                }

                It "SSH is allowed on Linux" {
                    $Group.IpPermissions | foreach FromPort | Should be 22
                }
            }
        }

        if ($PSBoundParameters.ContainsKey('AmiId'))
        {
            $Output = (Get-SSMAutomationExecution -AutomationExecutionId $ExecutionId | foreach StepExecutions | where StepName -eq 'LaunchInstance' | foreach Outputs)

            It "InstanceId present in output" {
                $Output.ContainsKey('InstanceIds') | should be $true
            }

            It "One instanceid in output" {
                $Output['InstanceIds'].Count | should be 1
            }

            $InstanceId = $Output['InstanceIds']
            It "Instance id is not empty" {
                $InstanceId | should not be [string]::empty
            }

            $Instances = (Get-EC2Instance -InstanceId $InstanceId)

            It "Only one instance created in EC2" {
                $Instances.Instances.Count | should be 1
            }
            $Instance = $Instances.Instances[0]

            It 'Instance created in EC2' {
                $Instance | should not be $null
            }

            It "Instance created with AmiId $AmiId" {
                $Instance.ImageId | should be $AmiId 
            }

            It "Instance created of type $InstanceType" {
                $Instance.InstanceType | should be $InstanceType
            }

            It "Instance created with KeyPair $KeyPairName" {
                $Instance.KeyName | should be $KeyPairName
            }

            It "Security Group created in instance" {
                $Instance.SecurityGroups[0].GroupName | should be $GroupName
            }

            $ManagedInstance = Get-SSMInstanceInformation -InstanceInformationFilterList @{Key='InstanceIds'; ValueSet="$InstanceId"}

            It "Instance $InstanceId created as a managed instance" {
                $ManagedInstance | should not be $null
            }
        }
    }
    catch {
        Write-Verbose "EXCEPTION OCCURRED" -Verbose
        Write-Verbose -Verbose $_.Exception 
        $_.Exception | should not throw
    }
    finally {

        if ($InstanceId -ne [string]::Empty)
        {
            Remove-EC2Instance -InstanceId $InstanceId -Force

            $count = 10
            Write-Progress -Activity "Instance Termination" -Status "Terminating instance $InstanceId" -PercentComplete $count
            do{
                if ($count -gt 90){
                    $count = 10
                }
                else {
                    $count +=1 
                }
                
                $status = (Get-EC2Instance -InstanceId $InstanceId).Instances[0].State
                Write-Progress -Activity "Instance Termination" -Status "Terminating instance $InstanceId" -PercentComplete $count
                sleep 1;
            }while($status.code -ne 48)
        }
        if ($PSBoundParameters.ContainsKey('RoleName'))
        {
            Get-IAMAttachedRolePolicies -RoleName $Rolename | Unregister-IAMRolePolicy -Rolename $RoleName -Force
            Remove-IAMRoleFromInstanceProfile -InstanceProfileName $Rolename -RoleName $RoleName -Force
            Remove-IAMRole -RoleName $RoleName -Force
        }

        if ($PSBoundParameters.ContainsKey('GroupName'))
        {
            Remove-EC2SecurityGroup -GroupName $GroupName -Force
        }

        if ($PSBoundParameters.ContainsKey('KeyPairName'))
        {
            Remove-EC2KeyPair -KeyName $KeyPairName -Force 
        }
    }        
}

function Create-Document {
    $script:Documents.Keys | %{
        New-SSMDocument -Name $_ -Content (Get-Content -Path $script:Documents[$_] -Raw) -DocumentType Automation
    }
}
Describe "DocumentTests" {

    BeforeAll {
        Delete-Document
    }

    $script:Documents.Keys | %{
        It "Create document $($_)" {
            New-SSMDocument -Name $_ -Content (Get-Content -Path $script:Documents[$_] -Raw) -DocumentType Automation | should not be [string]::empty  
        }
        It "Describe document $($_)" {
            Get-SSMDocument -Name $_ | should not be $null
        }
    }
    
     AfterAll {
        Delete-Document
    }
}

Describe "ManagedInstanceProfileTests" {
    BeforeAll {
        Delete-Document
        Create-Document
    }

    $RoleName = 'TestRole' + (New-Guid)
    Test-DocumentExecution -DocumentName $script:ManagedInstanceProfileDoc -RoleName $RoleName

    AfterAll {
        Delete-Document
    }
}

Describe "SecurityGroupWindowsTests" {
    BeforeAll {
        Delete-Document
        Create-Document
    }

    $GroupName = 'TestGroup' + (New-Guid)
    Test-DocumentExecution -DocumentName $script:SecurityGroupDoc -GroupName $GroupName -Platform 'Windows' 

    AfterAll {
        Delete-Document
    }
}

Describe "SecurityGroupLinuxTests" {

    BeforeAll {
        Delete-Document
        Create-Document
    }

    $GroupName = 'TestGroup' + (New-Guid)
    Test-DocumentExecution -DocumentName $script:SecurityGroupDoc -GroupName $GroupName -Platform 'Linux' 

    AfterAll {
        Delete-Document
    }
}
Describe "LinuxInstanceTests" {
    BeforeAll {
        Delete-Document
        Create-Document
    }

    $RoleName = 'TestRole' + (New-Guid)
    $GroupName = 'TestGroup' + (New-Guid)
    $KeyPairName = 'TestKeyPair' + (New-Guid)
    Test-DocumentExecution -DocumentName $script:ManagedInstanceLinuxDoc -RoleName $RoleName -GroupName $GroupName -AmiId $script:LinuxAmiId -InstanceType 't2.medium' -KeyPairName $KeyPairName -Platform 'Linux'

    AfterAll {
        Delete-Document
    }
}

Describe "WindowsInstanceTests" {
    BeforeAll {
        Delete-Document
        Create-Document
    }

    $RoleName = 'TestRole' + (New-Guid)
    $GroupName = 'TestGroup' + (New-Guid)
    $KeyPairName = 'TestKeyPair' + (New-Guid)
    Test-DocumentExecution -DocumentName $script:ManagedInstanceWindowsDoc -RoleName $RoleName -GroupName $GroupName -AmiId $script:WindowsAmiId -InstanceType 't2.medium' -KeyPairName $KeyPairName -Platform 'Windows'

    AfterAll {
        Delete-Document
    }
}

