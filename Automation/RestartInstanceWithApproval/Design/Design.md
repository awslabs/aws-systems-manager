# Retart EC2 instance based on ids or tags while requiring approval from at least one specified user

## Notes

Initial version will only support restart via instance IDs (not tags) but will be updated after we have a lambda function
that correctly determines InstanceIds from Tags and can pass those values to the next step in the Automation document.

## Document Design

Refer to schema.json

Document Steps:
  1. aws:approve
      * Inputs:
        * NotificationArn: {{SNSTopicArn}}
        * Message: "Please approve restarting the selected instance(s)"
        * MinRequiredApprovals: 1
        * Approvers: {{Approvers}}
  2. aws:changeInstanceState
    * Inputs:
      * DesiredState: stopped
      * InstanceIds: {{InstanceIds}}
  3. aws:changeInstanceState
    * Inputs:
      * DesiredState: running
      * InstanceIds: {{InstanceIds}}

## Test script

Python script will:
  1. Create 2 instances (instances 'a' & 'b')
  2. Verify the EC2 instances are in the running state
  3. Create the Automation Document
  4. Execute the document, which will go into the Waiting state pending approval
  5. Send the Approve signal via ssm_client.send_automation_signal() method, which will allow the automation to continue
  6. Verify the instances are in a running state and that no errors were encountered when executing the Automation document
  7. Destroy the instances and CloudFormation stack
