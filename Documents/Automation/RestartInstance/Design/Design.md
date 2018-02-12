# Start EC2 instance based on ids or tags

## Notes

Initial version will only support start via instance IDs (not tags) but will be updated after we have a lambda function
that correctly determines InstanceIds from Tags and can pass those values to the next step in the Automation document.

## Document Design

Refer to schema.json

Document Steps:
  1. aws:changeInstanceState
    * Inputs:
      * DesiredState: stopped
      * InstanceIds: {{InstanceId}}
  2. aws:changeInstanceState
    * Inputs:
      * DesiredState: running
      * InstanceIds: {{InstanceId}}

## Test script

Python script will:
  1. Create 2 instances (instances 'a' & 'b')
  2. Verify the EC2 instances are in the running state
  3. Create the Automation Document, which will stop the instances and then subsequently start them again
  4. Execute the document
  5. Verify the instances are in a running state and that no errors were encountered when executing the Automation document
  6. Destroy the instances and CloudFormation stack
