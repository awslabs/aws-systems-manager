# AWS-EnableSQSEncryption

## What does this document do?

The AWS-EnableSQSEncryption runbook enables encryption at rest for an existing Amazon Simple Queue Service (SQS) queue using the [SetQueueAttributes](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_SetQueueAttributes.html) API. An Amazon Simple Queue Service (SQS) queue can be encrypted with SQS managed encryption keys (SSE-SQS) or with keys managed by in the AWS Key-Management Service (SSE-KMS). The KMS key that you assign to your queue must have a key policy that includes permissions for all principals that are authorized to use the queue. With SSE enabled, anonymous SendMessage and ReceiveMessage requests to the encrypted queue will be rejected.

## Input Parameters

### AutomationAssumeRole

- **Type**: AWS::IAM::Role::Arn
- **Description**: (Optional) The Amazon Resource Name (ARN) of the AWS Identity and Access Management (IAM) role that allows Systems Manager Automation to perform the actions on your behalf. If no role is specified, Systems Manager Automation uses the permissions of the user that starts this runbook.
- **Default**: ""

### QueueUrl

- **Type**: String
- **Allowed Pattern**: `https?:\/\/(sqs\.)?[-a-zA-Z0-9@:%.\+~#=]{2,256}\.[a-z]{2,4}\b([-a-zA-Z0-9@:%\+_.-~#?&//=]{1,1024}$)`
- **Description**: (Required) The URL of the Amazon Simple Queue Service (SQS) queue whose attributes are set.

### KmsKeyId

- **Type**: String
- **AllowedPattern**: `^$|^[a-z0-9-]{1,2048}$|^mrk-[a-z0-9]{1,2044}$|^alias\/.{1,250}$|^arn:aws[a-z0-9-]*:kms:[a-z0-9-]+:\d{12}:key\/[a-z0-9-]{1,1992}$|^arn:aws[a-z0-9-]*:kms:[a-z0-9-]+:\d{12}:key\/mrk-[a-z0-9]{1,1988}$|^arn:aws[a-z0-9-]*:kms:[a-z0-9-]+:\d{12}:alias\/.{1,1990}$`
- **Default**: ""
- **Description**: (Optional) The GUID for the customer-managed AWS KMS key to use for encryption. This value can be a
    globally unique identifier, a fully specified Amazon Resource Name (ARN) to either an alias or a key, or an alias
    name prefixed by "alias/". You can also use a master key owned by SQS Queues by specifying the alias aws/sqs.

### KmsDataKeyReusePeriodSeconds

- **Type**: String
- **Allowed Pattern**: `^(0|[6-9]\d|[1-9]\d{2}|[1-9]\d{3}|[1-7]\d{4}|8[0-5]\d{3}|86[0-3]\d{2}|86400)$`
- **Default**: 300
- **Description**: (Optional) The length in time, in seconds for a minimum of 60 seconds and a max of 86400 seconds, for which an Amazon Simple Queue Service (SQS) queue can reuse a data key to encrypt or decrypt messages before calling KMS again.

### Required IAM Permissions

The `AutomationAssumeRole` parameter requires the following actions to use the runbook successfully.

- `ssm:StartAutomationExecution`
- `ssm:GetAutomationExecution`
- `sqs:GetQueueAttributes`
- `sqs:SetQueueAttributes`

## Document Steps

1. SelectKeyType (aws:branch): This step determines if the user will use the default SSE-SQS or SSE-KMS.
    1. Inputs
        1. NextStep: PutAttributeSseKms
        2. Variable: KmsKeyId
        3. Not StringEquals: ""
    2. Default
        1. NextStep: PutAttributeSseSqs

2. PutAttributeSseKms (aws:executeAwsApi): This step sets the Amazon Simple Queue Service (SQS) queue attribute with a user managed KMS Key.
    1. Inputs
        1. Service: SQS
        2. Api: SetQueueAttributes
        3. QueueUrl
        4. KmsKeyId
            1. Attributes.KmsMasterKeyId.$KmsKeyId
        5. KmsDataKeyReusePeriodSeconds
            1. Attributes.KmsDataKeyReusePeriodSeconds
    2. NextStep: VerifySqsEncryptionKms

3. PutAttributeSseSqs (aws:executeAwsApi): This step sets the Amazon Simple Queue Service (SQS) queue attribute with SSE-SQS.
    1. Inputs
        1. Service: SQS
        2. Api: SetQueueAttributes
        3. QueueUrl
        4. KmsKeyId
            1. Attributes.SqsManagedSseEnabled.True
    2. NextStep: VerifySqsEncryptionDefault

4. VerifySqsEncryptionKms (aws:assertAwsResourceProperty): This step verifies that the KMS Keys have been enabled on the Amazon Simple Queue Service (SQS) queue.
    1. Inputs
        1. Service: SQS
        2. Api: GetQueueAttributes
        3. QueueUrl
        4. KmsKeyId
        5. PropertySelector: Attributes.KmsMasterKeyId
        6. DesiredValues: KmsKeyId

5. VerifySqsEncryptionDefault (aws:assertAwsResourceProperty): This step verifies that the SQS Managed Keys have been enabled on the Amazon Simple Queue Service (SQS) queue.
    1. Inputs
        1. Service: SQS
        2. Api: GetQueueAttributes
        3. QueueUrl
        4. PropertySelector: Attributes.SqsManagedSseEnabled
        5. DesiredValues: true

## Tests

### Test Case 1: Enable SSE-SQS on a Queue

1. Launch CloudFormation that creates an Amazon Simple Queue Service (SQS) queue.
2. Execute automation script using default value for KmsKeyId, ‘aws/sqs’.
3. Verify successful document execution.
4. Verify SSE-SQS configuration of queue.

### Test Case 2: Enable SSE-KMS on a Queue

1. Launch CloudFormation that creates an Amazon Simple Queue Service (SQS) queue.
2. Execute automation document using existing KMS key and KmsDataKeyReusePeriodSeconds.
3. Verify successful document execution.
4. Verify SSE-KMS configuration of queue.

### Test Case 3: Enable SSE-SQS on a Queue that does not exist

1. Execute automation document using a randomized non-existent SQS instance name.
2. Verify automation document failure.

### Test Case 4: Enable SSE-KMS on a Queue that does not exist

1. Execute automation document using existing KMS key and KmsDataKeyReusePeriodSeconds using a randomized non-existent SQS instance name.
2. Verify automation document failure.

### Test Case 5: Enable SSE-KMS on a Queue with a key that does not exist

1. Launch CloudFormation that creates an Amazon Amazon Simple Queue Service (SQS) queue.
2. Execute automation document using non-existent KMS key and KmsDataKeyReusePeriodSeconds for QueueUrl in Step 1.
3. Verify automation document failure.

### Test Case 6: Enable SSE-KMS on a Queue with non existent Data Reuse Value

1. Launch CloudFormation that creates an Amazon Amazon Simple Queue Service (SQS) queue.
2. Execute automation document using  KMS key and non existent KmsDataKeyReusePeriodSeconds for QueueUrl in Step 1.
3. Verify automation document failure.
