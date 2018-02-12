# Attach EBS Volume

## Notes

Initial version will only support attaching an existing volume to an instance.

## Document Design

Refer to schema.json

Document Steps:
1. aws:createStack - Execute CloudFormation Template to attach the volume.
   * Parameters:
       * Device: {{Device}} - The device name (for example, /dev/sdh or xvdh).
       * InstanceId: {{InstanceId}} - The ID of the instance.
       * VolumeId: {{VolumeId}} - The ID of the EBS volume. The volume and instance must be within the same Availability Zone.
2. aws:deleteStack - Delete CloudFormation Template.

## Test script

Python script will:
  1. Create a test stack with an instance and a volume
  2. Execute automation document to attach volume to instance
  3. Ensure the automation has executed successfully
  4. Detach volume
  5. Clean up test stack
