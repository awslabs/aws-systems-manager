# Create an Amazon Machine Image (AMI)

## Notes

Create an Amazon Machine Image (AMI) from an Amazon EC2 instance

## Document Design

Refer to schema.json

Document Steps:
1. aws:createStack - Execute CloudFormation Template to create lambda.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     * Parameters: 
       * LambdaRole: {{LambdaAssumeRole}} - role assumed by lambda to create the Amazon Machine Image (AMI).
       * LambdaName: CreateImageLambda-{{automation:EXECUTION_ID}}
2. aws:invokeLambdaFunction - Execute Lambda to detach the volume
   * Inputs:
     * FunctionName: CreateImageLambda-{{automation:EXECUTION_ID}} - Lambda name to use
     * Payload:
        * InstanceId: {{InstanceId}} - The ID of the Amazon EC2 instance.
        * ExecutionId: {{automation:EXECUTION_ID}} - The execution id of the Automation document.
3. aws:deleteStack - Delete CloudFormation Template.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID

## Test script

Python script will:
  1. Create a test stack with the automation assumed role and Amazon EC2 instance
  2. Execute automation document create an Amazon Machine Image (AMI) of the Amazon EC2 instance
  4. Verify that the Amazon Machine Image is created
  5. Deregister the Amazon Machine Image and delete associated Snapshot.
  6. Clean up test stack
