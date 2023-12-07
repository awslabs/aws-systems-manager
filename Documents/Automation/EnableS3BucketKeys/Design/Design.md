# AWS-EnableS3BucketKeys

## What does this document do?

The AWS-EnableS3BucketKeys runbook enables S3 Bucket Keys on a specified S3 Bucket. This bucket-level key will create data keys for new objects during its lifecycle. If the KmsKeyId parameter is not specified, server-side encryption with Amazon S3 managed keys (SSE-S3) is the default encryption configuration. Note: S3 Bucket Keys aren't supported for dual-layer server-side encryption with AWS Key Management Service (AWS KMS) keys (DSSE-KMS).

## Input Parameters

### AutomationAssumeRole

- **Type**: AWS::IAM::Role::Arn
- **Description**: (Optional) The Amazon Resource Name (ARN) of the AWS Identity and Access Management (IAM) role that allows Systems Manager Automation to perform the actions on your behalf. If no role is specified, Systems Manager Automation uses the permissions of the user that starts this runbook.

### BucketName

- **Type**: AWS::S3::Bucket::Name
- **Description**: (Required) The name of the S3 bucket that will have Bucket Keys enabled.

## KmsKeyId

- **Type**: String
- **AllowedPattern**: `^$|^[a-z0-9-]{1,2048}$|^mrk-[a-z0-9]{1,2044}$|^alias\/.{1,250}$|^arn:aws[a-z0-9-]*:kms:[a-z0-9-]+:\d{12}:key\/[a-z0-9-]{1,1992}$|^arn:aws[a-z0-9-]*:kms:[a-z0-9-]+:\d{12}:key\/mrk-[a-z0-9]{1,1988}$|^arn:aws[a-z0-9-]*:kms:[a-z0-9-]+:\d{12}:alias\/.{1,1990}$`
- **Default**: ""
- **Description**: (Optional) The ARN, key ID, or the key alias of the of the KMS Key you want to use for server-side bucket encryption.

## Required IAM Permissions

The `AutomationAssumeRole` parameter requires the following actions to use the runbook successfully.

- `ssm:StartAutomationExecution`
- `ssm:GetAutomationExecution`
- `s3:PutEncryptionConfiguration`
- `s3:GetEncryptionConfiguration`

## Document Steps

1. ChooseEncryptionType (aws:branch): This step evaluates the KmsKeyId parameter to determine if SSE-S3 (AES256) or SSE-KMS will be used.
    1. Inputs
        1. NextStep: PutBucketKeysKMS
        2. Variable: KmsKeyId
        3. Not StringEquals: ""
    2. Default
        1. NextStep: PutBucketKeysAES256

2. PutBucketKeysKMS (aws:executeAwsApi): This step sets the BucketKeyEnabled property to True for the specified S3 Bucket using the specified KmsKeyId.
    1. Inputs
        1. Service: S3
        2. Api: PutBucketEncryption
        3. BucketName: The provided S3 bucket name.
        4. KmsKeyId: The ARN, key ID, or key alias of the KMS key used for SSE-KMS.
        5. ApplyServerSideEncryptionByDefault.SSEAlgorithm: aws:kms
        6. BucketKeyEnabled: True
    2. NextStep: VerifyS3BucketKeysEnabled

3. PutBucketKeysAES256 (aws:executeAwsApi): This step sets the BucketKeyEnabled property to True for the specified S3 Bucket with AES256 encryption.
    1. Inputs
        1. Service: S3
        2. Api: PutBucketEncryption
        3. BucketName: The provided S3 bucket name.
        4. ApplyServerSideEncryptionByDefault.SSEAlgorithm: AES256
        5. BucketKeyEnabled: True
    2. NextStep: VerifyS3BucketKeysEnabled

4. VerifyS3BucketKeysEnabled (aws:assertAwsResourceProperty): This step verifies that the S3 Bucket Keys have been enabled on the S3 Bucket.
    1. Inputs
        1. Service: S3
        2. Api: GetBucketEncryption
        3. PropertySelector: ServerSideEncryptionConfiguration.Rules[0].BucketKeyEnabled
        4. DesiredValues: True

## Tests

### Test Case 1: Enable Bucket Keys on an S3 Bucket with a specified KMS Key

1. Launch CloudFormation stack that creates an S3 bucket with ServerSideEncryption BucketKeyEnabled set to False and a KMS Key.
2. Execute automation document using newly created S3 bucket name and KMS Key as input.
3. Verify successful document execution.
4. Verify S3 Bucket Keys enabled.

### Test Case 2: Enable Bucket Keys on an S3 Bucket without a specified KMS Key

1. Launch CloudFormation stack that creates an S3 bucket with ServerSideEncryption BucketKeyEnabled set to False.
2. Execute automation document using newly created S3 bucket name as input and do not specify KmsKeyId parameter.
3. Verify successful document execution.
4. Verify S3 Bucket Keys enabled.

### Test Case 3: Enable Bucket Keys with SSE-S3 encryption on Bucket that has SSE-KMS encryption and Bucket Keys already enabled

1. Launch CloudFormation stack that creates an S3 bucket with ServerSideEncryption BucketKeyEnabled set to True with SSE-KMS encryption.
2. Execute automation document using newly created S3 bucket name as input and do not specify KmsKeyId parameter.
3. Verify successful document execution.
4. Verify S3 Bucket Keys enabled with SSE-S3 encryption.

### Test Case 4: Enable Bucket Keys with SSE-KMS encryption on Bucket that has SSE-S3 encryption and Bucket Keys already enabled

1. Launch CloudFormation stack that creates an S3 bucket with ServerSideEncryption BucketKeyEnabled set to True with SSE-S3 encryption and a KMS Key.
2. Execute automation document using newly created S3 bucket name as input and specify the KmsKeyId.
3. Verify successful document execution.
4. Verify S3 Bucket Keys enabled with SSE-KMS encryption.

### Test Case 5: Enable Bucket Keys with SSE-S3 encryption on Bucket that has SSE-S3 encryption and Bucket Keys already enabled

1. Launch CloudFormation stack that creates an S3 bucket with ServerSideEncryption BucketKeyEnabled set to True with SSE-S3 encryption.
2. Execute automation document using newly created S3 bucket name as input and do not specify KmsKeyId parameter.
3. Verify successful document execution.
4. Verify S3 Bucket Keys enabled with SSE-S3 encryption.

### Test Case 6: Enable Bucket Keys with SSE-KMS encryption on Bucket that has SSE-KMS encryption and Bucket Keys already enabled

1. Launch CloudFormation stack that creates an S3 bucket with ServerSideEncryption BucketKeyEnabled set to True with SSE-KMS encryption and a different KMS Key.
2. Execute automation document using newly created S3 bucket name as input and specify the KmsKeyId parameter.
3. Verify successful document execution.
4. Verify S3 Bucket Keys enabled with SSE-KMS encryption.

### Test Case 7: Enable Bucket Keys on a non-existent S3 Bucket

1. Launch CloudFormation stack that creates an S3 bucket with ServerSideEncryption BucketKeyEnabled set to False.
2. Delete S3 bucket from test code.
3. Execute automation document using deleted S3 bucket name as input.
4. Verify document failure.
