# "Delete Amazon Machine Image (AMI) and all associated snapshots."

## Notes

Deletes the specified Amazon Machine Image (AMI) and all related snapshots.

## Document Design

Refer to schema.json

Document Steps:
1. aws:deleteImage - Deletes the Amazon Machine Image (AMI) and all related snapshots.
   * Inputs:
     * ImageId: {{ImageId}} - The ID of the Amazon Machine Image (AMI).
	 

## Test script

Python script will:
  1. Create a test stack with the automation assumed role and Amazon EC2 Instance.
  2. Create an Amazon Machine Image (AMI) from the Amazon EC2 Instance.
  3. Execute automation document to delete the specified Amazon Machine Image (AMI) and associated Snapshot.
  3. Deregister the Amazon Machine Image (AMI) and delete associated Snapshot
  4. Verify that the Amazon Machine Image (AMI) and associated Snapshot has been deleted
  5. Clean up test stack
