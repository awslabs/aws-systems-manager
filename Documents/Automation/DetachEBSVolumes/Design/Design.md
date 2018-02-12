# Detach EBS Volume

## Notes

Initial version will only support detaching an unmounted volume from an instance.

## Document Design

Refer to schema.json

Document Steps:
1. aws:createStack - Execute CloudFormation Template to create lambda.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     * Parameters: 
       * LambdaRole: {{LambdaAssumeRole}} - role assumed by lambda to detach the volume from the instance
       * LambdaName: UpdateCFTemplate-{{automation:EXECUTION_ID}}
2. aws:invokeLambdaFunction - Execute Lambda to detach the volume
   * Inputs:
     * FunctionName: UpdateCFTemplate-{{automation:EXECUTION_ID}} - Lambda name to use
     * Payload:
        * VolumeId: {{VolumeId}} - The ID of the EBS volume. The volume and instance must be within the same Availability Zone.
3. aws:deleteStack - Delete CloudFormation Template.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID

## Test script

Basic Test will:
  1. Create a test stack with an instance and a volume
  2. Execute automation document to detach the volume from the instance
  3. Ensure the automation has executed successfully
  4. Clean up test stack

Mounted Test Test will:
  1. Create a test stack with an instance and a volume
  2. Mount the volume on the instance
  2. Execute automation document to detach the volume from the instance
  3. Ensure the automation has executed failed
  4. Clean up test stack
