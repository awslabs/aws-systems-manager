# Create Snapshot

## Notes

This will create a snapshot

## Document Design

Refer to schema.json

Document Steps:
1. aws:createStack - Execute CloudFormation Template to create lambda.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     * Parameters: 
       * LambdaRole: {{LambdaAssumeRole}} - role assumed by lambda to create the snapshot.
       * LambdaName: CreateSnapshotLambda-{{automation:EXECUTION_ID}}
2. aws:invokeLambdaFunction - Execute Lambda to detach the volume
   * Inputs:
     * FunctionName: CreateSnapshotLambda-{{automation:EXECUTION_ID}} - Lambda name to use
     * Payload:
        * VolumeId: {{VolumeId}} - The ID of the EBS volume.
        * Description: {{Description}} - A description for the EBS snapshot.
3. aws:deleteStack - Delete CloudFormation Template.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID

## Test script

Python script will:
  1. Create a test stack with the automation assumed role and volume
  2. Execute automation document create a snapshot of that volume
  4. Verify that the snapshot is created
  5. Delete the snapshot
  6. Clean up test stack
