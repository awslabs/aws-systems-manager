# Encrypt EBS root volume

## Notes

Encrypts the root volume of an EC2 instance.  This will be a replace operation and not an in-line encryption operation.

## Document Design

Refer to schema.json

Document Steps:
1. Create automation service role  
   * Create a role with following policies:  
     •	AmazonEC2FullAccess (AWS Managed)  
     •	AmazonSSMAutomationRole (AWS Managed)  
     •	AWSKeyManagementServicePowerUser (AWS Managed)  
     In addition, following inline policies must be created and attached
```json
     •	createlambda (inline)  
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": [
                        "lambda:CreateFunction",
                        "lambda:GetFunction",
                        "lambda:DeleteFunction"
                    ],
                    "Resource": "*",
                    "Effect": "Allow"
                },
                {
                    "Action": [
                        "iam:GetRole",
                        "iam:PassRole",
                        "iam:DeleteRolePolicy",
                        "iam:CreateRole",
                        "iam:DeleteRole",
                        "iam:PutRolePolicy"
                    ],
                    "Resource": "arn:aws:iam::*:role/*",
                    "Effect": "Allow"
                }
            ]
        }
```

```json
     •  ebsvolumepermission (inline)  
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": [
                        "ec2:AttachVolume",
                        "ec2:DetachVolume"
                    ],
                    "Resource": "arn:aws:ec2:*:*:instance/*",
                    "Effect": "Allow"
                },
                {
                    "Action": [
                        "ec2:AttachVolume",
                        "ec2:DetachVolume"
                    ],
                    "Resource": "arn:aws:ec2:*:*:volume/*",
                    "Effect": "Allow"
                }
            ]
        }
```  

```json
     •  invokeLambdaFunction  (inline)  
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "lambda:InvokeFunction",
                    "Resource": [
                        "arn:aws:lambda:*:*:function:*"
                    ],
                    "Effect": "Allow"
                }
            ]
        }
```  

```json
     •	kmsaccess (inline)  
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": [
                        "kms:*"
                    ],
                    "Resource": [
                        "*"
                    ],
                    "Effect": "Allow"
                }
            ]
        }
```  

2. aws:npark-encryptrootvolume - Execute CloudFormation Template to attach the volume.
   * Parameters:
       * instanceId: (Required) Instance ID of the ec2 instance whose root volume needs to be encrypted
       * KmsKeyId: (Required) Customer KMS key to use during the encryption
       * AutomationAssumeRole: (Optional) The ARN of the role that allows Automation to perform the actions on your behalf. See step 1 for details.

## Test script

Python script will:
#  1. Create a test stack with an instance, a volume and a KMS Key (Customer managed)
#  2. Execute automation document to replace the root volume with the encrypted one (after a copy operation of the root volume snapshot)
#  3. Ensure the Automation has executed successfull
#  4. Clean up test stack
