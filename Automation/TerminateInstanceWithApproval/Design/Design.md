# Terminate EC2 instance based on ids or tags with approval

## Notes

Initial version will only support termination via instance IDs (not tags) to avoid Lambda use.

## Document Design

Refer to schema.json

Document Steps:
  1. aws:approve
    * Inputs:
      * NotificationArn: {{SNSTopicArn}}
      * Message: "Please approve terminating the selected instance(s)"
      * MinRequiredApprovals: 1
      * Approvers: {{Approvers}}
  2. aws:changeInstanceState
    * Inputs:
      * DesiredState: terminated
      * InstanceIds: {{InstanceIds}}

## Test script

Python script will:
  1. Create 2 instances (instances 'a' & 'b') via CloudFormation template, which will start the instances automatically
  2. Create the Automation Document
  3. Execute the document for instances 'a' & 'b'
  4. Check that the automation execution enters the Waiting state (pending approval)
  5. Use ssm_client.send_automation_signal with SignalType 'Approve' to programmatically approve the execution
  6. Wait until the automation execution completes with a status of 'Success'
  7. Verify that the EC2 instances are now in the terminated state
  8. Tear down the CloudFormation stack
