# Patch Windows instances in an Auto Scaling Group

## Document Design

Refer to schema.json

## Test script

Python script will:
  1. Create ASG with 2 instances (min:1, max: 2, desired: 2)
  2. Create the Automation Document
  3. Run the automation document against one of the instances
  4. Poll the ASG and verify the instance enters standby
  5. Verify the Automation completes with a successful status
  6. Destroy the ASG
