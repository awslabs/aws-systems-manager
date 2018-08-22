# Create an Amazon Machine Image (AMI)

## Notes

Create an Amazon Machine Image (AMI) from an Amazon EC2 instance

## Document Design

Refer to schema.json

Document Steps:
1. aws:createImage - Creates a new AMI from an Amazon EC2 instance
   * Inputs:
     * InstanceId: {{InstanceId}} - The ID of the Amazon EC2 instance.

## Test script

Python script will:
  1. Create a test stack with the automation assumed role and Amazon EC2 instance
  2. Execute automation document create an Amazon Machine Image (AMI) of the Amazon EC2 instance
  3. Verify that the Amazon Machine Image is created
  4. Deregister the Amazon Machine Image and delete associated Snapshot.
  5. Clean up test stack
