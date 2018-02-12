# Resize Instance

## Notes

Resize an instance by changing the instance type

The bulk of the time spent is starting the instance.  It takes approximately 5 minutes to restart the instance because it needs wait for the status check

## Document Design

Refer to schema.json

Document Steps:
1. aws:createStack - Execute CloudFormation Template to create lambda.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     * Parameters: 
       * LambdaRole: {{LambdaAssumeRole}} - role assumed by lambda to resize an instance
       * LambdaName: ResizeInstanceLambda-{{automation:EXECUTION_ID}}
2. aws:changeInstanceState - Stops the instance.
      * Inputs:
        * InstanceIds: {{InstanceId}} - Instance ID to stop
        * DesiredState: 'stopped'
3. aws:invokeLambdaFunction - Execute Lambda to change the instance type of an instance
   * Inputs:
     * FunctionName: ResizeInstanceLambda-{{automation:EXECUTION_ID}} - Lambda name to use
     * Payload:
        * InstanceId: {{InstanceId}} - The ID of the instance.
        * InstanceType: {{InstanceType}} - The instance type.
4. aws:changeInstanceState - Restart the instance.
   * Inputs:
     * InstanceIds: {{InstanceId}} - Instance ID to start
     * DesiredState: 'running'
5. aws:deleteStack - Delete CloudFormation Template.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID

## Test script

Python script will:
  1. Create a test stack with an instance
  2. Execute automation document to attach volume to instance
  3. Verify instance type of a stack has changed
  4. Verify instance is up
  5. Clean up test stack
