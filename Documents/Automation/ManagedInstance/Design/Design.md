# Deploy Managed Instance

## Document Design

Refer to schema.json

### Steps

1. Create CloudFormation Template
   * Delete Template on failure 
   * **Steps:**
     1. Create Lambda Role if not passed in.
     2. Create Instance Profile if it does not exist or use profile found in the account.
     3. Create Security Group if it does not exist or use Security Group found in the account.
     4. Add Security Group Ingress if it does not exist.
     5. Create Instance
        * Pass in UserData if linux defined as Map in the CloudFormation Template.
   * **CloudFormation Rollback**
     * Instance Profile will be deleted if it was created in this template.
     * Security Group will be deleted if it was created in this template.
2. Delete CloudFormation Template
   * **CloudFormation**
     * Instance Profile - Retains the instance profile created by this lambda.
     * Security Group - Retain the security group created by this lambda.
     * Instance - configured to retain on delete.

## Tests

### test_collection_info.py

Tests collection of windows/linux AMI information and VPC information used for this document.

### test_create_instance_profile.py

Tests creating instances profile and handling of existing profile.

### test_security_group.py

Tests creation security group and handling of existing security group.

### test_security_group_ingress

Tests adding ingress to security group. 

### test_document.py

Integration test of aws-CreateManagedInstance.json

1. Executes document aws-CreateManagedInstance.json
2. Validates Instance created is configured correctly.

## Makefile

This document requires the document to include some codes inline for both CloudFormation Template and the SSM Document.
The makefile is here to help facilitate this process.

### Building Document

```
make
```

1. Parse CloudFormation Template
2. Embed lambda function located in Documents/Lambdas/*.py into CloudFormation Template
3. Parse Documents/aws-CreateManagedInstance.json
4. Embed CloudFormation Template into Document.
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
python -m unittest Tests.test_ami_info.AmiInfoTest.test_handler_on_create_windows
```