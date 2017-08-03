# Configure SSM Agent CloudWatch Logging

Amazon EC2 Systems Manager Document to configure SSM Agent logging to CloudWatch Logs. The document updates the logging configuration file. It can be used to change log level or add CloudWatch Logs as a logging destination. By enabling CloudWatch upload, all logs of SSM Agent would also be streamed to the CloudWatch instance in addition to the being added to the log file on disk.

## Type of Document

*Command* Document - Can be used with RunCommand

## Supported Platforms

Supported for *Windows*, *Linux*

## Supported SSM Agent Versions

Agent Version 2.0.902.0 and above

## Parameters

### LogLevel

Specify the Log Level of SSM Agent logs. This would change the log level for all logging destinations specified (file/console/cloudwatch/others)

### EnableCloudWatchUpload

On setting this to true, SSM Agent will start logging to CloudWatchLogs of the AWS Account and in the region it is running. Setting it to false will disable the logging to CloudWatchLogs.

### LogGroup

(Optional) Specify the log group name for logging in CloudWatchLogs. The log group would be created if not already present. If not specified, the logs would be present in the default log group 'SSMAgentLogs'.

### EnableShare

(Optional) On setting it to true, SSM Agent will start logging to the destination specified in 'ShareDestination'. The destination needs to be passed if this parameter is true. Default value false.

### ShareDestination

(Optional) External AWS Account CloudWatch destination in the format 'IAMUserAccessKeyID::IAMUserSecretAccessKey::DestinationLogGroup::DestinationLogStream'. The IAM User should have access to DescribeLogStreams, PutLogEvents on the destination CloudWatchLogs log group. The log group and stream should be present. Parameter will be ignored if EnableShare is false. The destination must follow the regex pattern ```(^[\w]+::.+::[\.\-_/#A-Za-z0-9]+::[^:*]+$)|^$```.

## Details

Executing the document will update the seelog.xml file used by SSM agent with the configurations being passed as parameters. The Agent will pick the latest logging configurations and depending on the parameters may:
- Change the log level of SSM Agent
- Enable/Disable logging to CloudWatchLogs
- Enable/Disable logging to external AWS Account's CloudWatchLogs

## Dependencies
For Linux, the XML modification would install XMLStarlet command line utility (under MIT license) if not already installed.
