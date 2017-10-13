# Start EC2 instance based on ids or tags

## Notes

Initial version will only support start via instance IDs (not tags) to avoid Lambda use in first document.

## Document Design

Refer to schema.json

Document Steps:
  1. aws:changeInstanceState
    * Inputs:
      * DesiredState: running
      * InstanceIds: {{InstanceIds}}

## Test script

Python script will:
  1. Create 3 instances (instances 'a', 'b', & 'c')
  2. Stop the 3 instances
  3. Create the Automation Document
  4. Execute the document twice: once for instance 'a' (to test invocation with a single instance), and again for instances 'b' & 'c' (to test a list of instances)
  5. Verify the instances are in a running state
  6. Destroy the instances
