# Delete CloudFormation stacks based on their name/ID

## Notes

The IAM role used for the AutomationAssumeRole parameter must have the following permissions assigned (see 
http://docs.aws.amazon.com/systems-manager/latest/userguide/automation-actions.html#automation-action-deletestack):

```json
{
   "Version":"2012-10-17",
   "Statement":[
      {
         "Effect":"Allow",
         "Action":[
            "sqs:*",
            "cloudformation:DeleteStack",
            "cloudformation:DescribeStacks"
         ],
         "Resource":"*"
      }
   ]
}
```

## Document Design

Refer to schema.json

Document Steps:
  1. aws:deleteStack
  * Inputs:
    * StackName: {{StackNameOrId}} - Stack name or unique ID

## Test script

Python script will:
  1. Create CloudFormation stack from template
  2. Ensure stack is running
  3. Execute the automation document which will tear down and delete the stack
  4. Ensure the automation has executed successfully
  5. Query the CloudFormation API to ensure the stack has been successfully deleted
