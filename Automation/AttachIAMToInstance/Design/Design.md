# Attach an IAM role to an Instance

## Notes

To associate a role to an instance, we have to create an instance profile.
By AWS Design, we can only have one role associated to an instance profile. 
So the new instance profile name will be the name of the role. 
Then we can associate the instance to an instance profile.

There are two things to consider about attaching a role to an instance
1. Instance is already associated to a role
2. Instance is not associated to any role

## Document Design

Refer to schema.json

Document Steps:
1. aws:createStack - Execute CloudFormation Template to create lambda.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     * Parameters: 
       * LambdaRole: {{LambdaAssumeRole}} - role assumed by lambda
       * LambdaName: UpdateCFTemplate-{{automation:EXECUTION_ID}}
2. aws:invokeLambdaFunction - Execute Lambda to detach the volume
   * Inputs:
     * FunctionName: AttachIAMToInstanceLambda-{{automation:EXECUTION_ID}} - Lambda name to use
     * Payload:
        * Instance: {{Instance}} - The ID of the instance.
        * RoleName: {{RoleName}} - Role Name to associate the Instance
3. aws:deleteStack - Delete CloudFormation Template.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID

## Test script

Instance is already associated to a role:
  1. Create a test stack with an instance already associated to a role
  2. Execute automation document to attach the role to an instance
  3. Verify instance profile is replaced
  4. Clean up test stack

Instance is not associated to a role:
  1. Create a test stack with an instance that is not associated to any role
  2. Execute automation document to attach the role to an instance
  3. Verify instance is associated to the role
  4. Clean up test stack

