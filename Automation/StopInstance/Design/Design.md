# Stop EC2 instance based on ids or tags

## Notes

Initial version will only support stop via instance IDs (not tags) to avoid Lambda use.

## Document Design

Refer to schema.json

Document Steps:
  1. aws:changeInstanceState
    * Inputs:
      * DesiredState: stopped
      * InstanceIds: {{InstanceIds}}

## Test script

Python script will:
  1. Create 2 instances (instances 'a' & 'b')
  2. Stop the 2 instances
  3. Create the Automation Document
  4. Execute the document for instances 'a' & 'b' (to test a list of instances)
  5. Verify the instances are in the 'stopped' state
  6. Destroy the instances
