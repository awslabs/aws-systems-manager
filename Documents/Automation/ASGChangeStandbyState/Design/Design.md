# Change Standby state of instances within an autoscaling group

## Document Design

Refer to schema.json

### Steps

1. Create CloudFormation Template
   * CloudFormation template will create a lambda function that can change the standby state of an instance in an ASG
2. Execute lambda
   * Lambda function take parameters for ASG name, instance ID, and which state to put the instance into (either EitherStandby or ExitStandby)
3. Delete CloudFormation Template
   * Deleting the CF template will destroy any created IAM roles as well as the deployed Lambda

## Tests

### tests.py

The tests for both Enter and Exit standby are defined in this file, with separate test functions for each action.

## Makefile

This document requires the document to include some inline code for both CloudFormation Template and the SSM Document.
The makefile is here to help facilitate this process.

### Building Document

```
make
```

1. Parse CloudFormation Template
2. Embed lambda function located in Documents/Lambdas/change_asg_state.py into CloudFormation Template
3. Parse Documents/aws-ASGChangeStandbyState.json
4. Embed CloudFormation Template into Automation Document.
5. Output new Document into ./Output

### Cleaning Document

```
make clean
```

1. Delete content of ./Output folder

### Test

```
make test
```

1. Discover all test in this folder.
2. Execute all tests

**Note**: You can also run individual test by telling python unit test framework which test to run, but make sure to run
`make` before actually running any tests.

```
python -m unittest Tests.tests.TestCase.test_enter_standby_document
python -m unittest Tests.tests.TestCase.test_exit_standby_document
```