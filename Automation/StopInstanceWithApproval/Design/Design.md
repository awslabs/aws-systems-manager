# Stop EC2 instances with approval

## Document Design

Refer to schema.json

Document Steps:
  1. aws:approve
    * Inputs:
      * NotificationArn: {{SNSTopicArn}}
      * Message: "Please approve stopping the selected instance(s)"
      * MinRequiredApprovals: 1
      * Approvers: {{Approvers}}
  2. aws:changeInstanceState
    * Inputs:
      * DesiredState: stopped
      * InstanceIds: {{InstanceId}}

## Test script

Python script will:
  1. Create 2 instances (instances 'a' & 'b') & a dummy SNS topic using a CloudFormation template
  2. Verify that the instances are in the running state
  3. Create the Automation Document
  4. Execute the automation document
  5. Use ssm_client.send_automation_signal with SignalType 'Approve' to automatically approve the execution
  6. Verify the instances are in a stopped state
  7. Destroy the instances, delete the Automation Document, and delete the dummy SNS topic
