# Configure CloudWatch on EC2 Instance

Establishes CloudWatch monitoring on an EC2 Instance

## Inputs

#### InstanceId
  * The EC2 instance for which CloudWatch monitoring will be established.
  * Type: String
  * Required: True
  
#### status
  * Specifies whether to Enable or disable CloudWatch. Valid values: "Enabled" | "Disabled", defaults to "Enabled"
  * Type: String
  * Required: False
   
#### properties
  * The configuration for CloudWatch in JSON format. See http://docs.aws.amazon.com/ssm/latest/APIReference/aws-cloudWatch.html
  * Type: String
  * Required: False

## Outputs
The automation execution has no outputs.
