# Terminate EC2 instance based on ids or tags

## Notes

Initial version will only support termination via instance IDs (not tags) to avoid Lambda use.

## Document Design

Refer to schema.json

Document Steps:
  1. aws:changeInstanceState
    * Inputs:
      * DesiredState: terminated
      * InstanceIds: {{InstanceId}}

## Test script

Python script will:
  1. Create 2 instances (instances 'a' & 'b') via CloudFormation template, which will start the instances automatically
  2. Create the Automation Document
  3. Execute the document for instances 'a' & 'b'
  4. Verify the instances are in the 'terminated' state and that the automation execution status is marked 'Success'
  5. Tear down the CloudFormation stack
