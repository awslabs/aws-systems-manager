# Copy Snapshot

## Notes

This will copy a snapshot

## Document Design

Refer to schema.json

Document Steps:
1. aws:createStack - Execute CloudFormation Template to create lambda.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     * Parameters: 
       * LambdaRole: {{LambdaAssumeRole}} - The ARN of the role assumed by lambda.
       * LambdaName: CopySnapshotLambda-{{automation:EXECUTION_ID}}
2. aws:invokeLambdaFunction - Execute Lambda to detach the volume
   * Inputs:
     * FunctionName: CopySnapshotLambda-{{automation:EXECUTION_ID}} - Lambda name to use
     * Payload:
        * SnapshotId: {{SnapshotId}} - The ID of the EBS snapshot to copy.
        * Region: {{Region}} - The ID of the EBS snapshot to copy.
        * Description: {{Description}} - A description for the EBS snapshot.
3. aws:deleteStack - Delete CloudFormation Template.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID

## Test script

Python script will:
  1. Create a test stack with the assumed role and volume
  2. Create a snapshot
  3. Execute automation document to copy the snapshot
  4. Verify that the snapshot exists
  5. Clean up delete the snapshot, (if exists)
  6. Clean up test stack