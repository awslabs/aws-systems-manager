# Encrypt EBS root volume

## Notes

Encrypts the root volume of an EC2 instance.  This will be a replace operation and not an in-line encryption operation.

## Document Design

Refer to schema.json

Document Steps:
1. aws:npark-encryptrootvolume - Execute CloudFormation Template to attach the volume.
   * Parameters:
       * instanceId: (Required) Instance ID of the ec2 instance whose root volume needs to be encrypted
       * region: (Required) Region in which the ec2 instance belong
       * KmsKeyId: (Required) Customer KMS key to use during the encryption
       * devicename: (Optional) Device name of the root volume.  Defaults to /dev/sda1
       * AutomationAssumeRole: (Optional) The ARN of the role that allows Automation to perform the actions on your behalf

## Test script

Python script will:
#  1. Create a test stack with an instance, a volume and a KMS Key (Customer managed)
#  2. Execute automation document to replace the root volume with the encrypted one (after a copy operation of the root volume snapshot)
#  3. Ensure the Automation has executed successfull
#  4. Clean up test stack
