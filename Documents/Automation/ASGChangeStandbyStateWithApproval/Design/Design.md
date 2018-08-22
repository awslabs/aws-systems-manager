# Change Standby state of instances within an autoscaling group with approval

## Document Design

Refer to schema.json

### Steps

1. Require approval for further execution
   * Once execution is approved, the next steps will occur
2. Create CloudFormation Template
   * CloudFormation template will create a lambda function that can change the standby state of an instance in an ASG
3. Execute lambda
   * Lambda function take parameters instance ID and the state to put the instance into (either EitherStandby or ExitStandby)
4. Delete CloudFormation Template
   * Deleting the CF template will destroy any created IAM roles as well as the deployed Lambda

## Tests

### tests.py

The tests for both Enter and Exit standby are defined in this file, with separate test functions for each action.

### Building Document and Test

1. Change directory to /Automation/ASGChangeStandbyState/
2. Run ```make```
3. In the AWS console, navigate to the EC2 screen and select "Documents" under "SYSTEMS MANAGER SHARED RESOURCES" on the left-hand menu.
4. Click Create Document
5. Enter the name awstest-ASGEnterStandby
6. Select "Automation" as the document type
7. Copy and paste the contents of /Automation/ASGChangeStandbyState/Output/aws-ASGEnterStandby.json into the Content text area.
8. Click "Create Document" 
9. Do the same for the exit standby document, substituting "awstest-ASGExitStandby" for the document name, and copy the contents of 
   /Automation/ASGChangeStandbyState/Output/aws-ASGExitStandby.json into the document.
10. Change directory to /Automation/ASGChangeStandbyStateWithApproval/ and run ```python tests.py```