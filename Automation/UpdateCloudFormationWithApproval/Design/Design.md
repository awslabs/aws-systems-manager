# Update CloudFormation Template

## Document Design

Refer to schema.json

### Steps

1. aws:approve
   * Inputs:
     * NotificationArn: {{SNSTopicArn}}
     * Message: "Approval required to update CloudFormation stack: {{StackNameOrId}}"
     * MinRequiredApprovals: 1
     * Approvers: {{Approvers}}
2. aws:createStack - Execute CloudFormation Template to create lambda.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     * Parameters: 
       * LambdaRole: {{LambdaAssumeRole}} - role assumed by lambda to update the CloudFormation Template.
       * LambdaName: UpdateCFTemplate-{{automation:EXECUTION_ID}}
3. aws:invokeLambdaFunction - Execute Lambda to update CloudFormationTemplate.
   * Inputs:
     * FunctionName: UpdateCFTemplate-{{automation:EXECUTION_ID}} - Lambda name to use
     * Payload:
       * StackName: {{StackName}} - Stack to update
       * TemplateLocation: {{TemplateLocation}} - Location of template (e.g. https://s3.amazonaws.com/example/updated.template)
4. aws:deleteStack - Delete CloudFormation Template.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID

### CloudFormation Template

Creates Lambda used by the SSM document to update the CloudFormation Template

#### Resources

* IAM Role - Role used by lambda (only created if non specified by user {{LambdaRoleArn}})
* Lambda - does the actual work to update the CloudFormation Template.

## Tests

### test_update_formation_template.py

Tests updating cloudformation template at the lambda level.

### test_document.py

Full SSM integration test.

1. Create a bucket for test in us-west-2
2. Deploy CloudFormation Template in us-east-1
   * Create IAM Role
3. Upload updated CloudFormation template to test bucket in us-west-2
   * Add another policy to the IAM Role. 
4. Execute SSM document to update CloudFormation Template.
5. Send automation signal.
6. Validate document executed correctly.
7. Validate new policy was added to IAM Role.
