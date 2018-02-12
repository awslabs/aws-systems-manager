# Delete Snapshot

## Notes

This will delete a snapshot

## Document Design

Refer to schema.json

Document Steps:
1. aws:createStack - Execute CloudFormation Template to create lambda.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     * Parameters: 
       * LambdaRole: {{LambdaAssumeRole}} - role assumed by lambda to delete the snapshot.
       * LambdaName: DeleteSnapshotLambda-{{automation:EXECUTION_ID}}
2. aws:invokeLambdaFunction - Execute Lambda to detach the volume
   * Inputs:
     * FunctionName: DeleteSnapshotLambda-{{automation:EXECUTION_ID}} - Lambda name to use
     * Payload:
        * SnapshotId: {{SnapshotId}} - The ID of the EBS volume. The volume and instance must be within the same Availability Zone.
3. aws:deleteStack - Delete CloudFormation Template.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID

## Test script

Python script will:
  1. Create a test stack with a volume
  2. Create a snapshot
  3. Execute automation document to delete a snapshot
  4. Verify that the snapshot does not exist
  5. Clean up delete the snapshot, (if exists)
  6. Clean up test stack
