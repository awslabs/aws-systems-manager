#
# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#!/usr/bin/env python

import os
import sys
import logging
import unittest

import ConfigParser
import boto3
import json

import time

DOC_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPOROOT = os.path.dirname(DOC_DIR)

# Import shared testing code
sys.path.append(
    os.path.join(
        REPOROOT,
        'Testing'
    )
)
sys.path.append(os.path.join(
    DOC_DIR, "Documents/Lambdas"
))
sys.path.append(
    os.path.abspath(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "lib/"
    ))
)
import ssm_testing

CONFIG = ConfigParser.ConfigParser()
CONFIG.readfp(open(os.path.join(REPOROOT, 'Testing', 'defaults.cfg')))
CONFIG.read([os.path.join(REPOROOT, 'Testing', 'local.cfg')])

REGION = CONFIG.get('general', 'region')
PREFIX = CONFIG.get('general', 'resource_prefix')

WINDOWS_AMI_ID = CONFIG.get('windows', 'windows2016.{}'.format(REGION))
LINUX_AMI_ID = CONFIG.get('linux', 'ami')
INSTANCE_TYPE = CONFIG.get('windows', 'instance_type')

SSM_DOC_NAME = PREFIX + 'update-cf-template'
CFN_STACK_NAME = PREFIX + 'update-cf-template'
TEST_CFN_STACK_NAME = PREFIX + 'test-update-cf-template'
TEST_S3_BUCKET = PREFIX + 'test-s3-bucket'
LAMBDA_ROLE = PREFIX + 'update-cf-lambda-role'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

boto3.setup_default_session(region_name=REGION)

iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
sts_client = boto3.client('sts')


def cleanup_bucket():
    try:
        # There shouldn't be anything else in this bucket
        s3_client.delete_object(
            Bucket=TEST_S3_BUCKET,
            Key='TestUpdateTemplate.yml')
    except Exception:
        pass

    try:
        s3_client.delete_bucket(
            Bucket=TEST_S3_BUCKET
        )
    except Exception:
        LOGGER.info("Was not able to delete S3 bucket correctly.")


def cleanup_role():
    try:
        iam_client.detach_role_policy(
            RoleName=LAMBDA_ROLE,
            PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
        )
    except Exception as e:
        LOGGER.info(e)

    try:
        iam_client.delete_role(RoleName=LAMBDA_ROLE)
    except Exception as e:
        LOGGER.info(e)


def create_role(user_arn):
    assume_role = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "lambda.amazonaws.com",
                        "ssm.amazonaws.com"
                    ]
                },
                "Action": "sts:AssumeRole"
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": user_arn},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    result = iam_client.create_role(RoleName=LAMBDA_ROLE, AssumeRolePolicyDocument=json.dumps(assume_role))
    iam_client.attach_role_policy(RoleName=LAMBDA_ROLE, PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess")

    # For what ever reason assuming a role that got created too fast fails, so we just wait until we can.
    retry_count = 6
    while True:
        try:
            sts_client.assume_role(RoleArn=result["Role"]["Arn"], RoleSessionName="checking_assume")
            break
        except Exception as e:
            retry_count -= 1
            if retry_count == 0:
                raise e

            LOGGER.info("Unable to assume role... trying again in 10 sec")
            time.sleep(10)

    return result


class DocumentTest(unittest.TestCase):
    def test_update_document(self):
        cfn_client = boto3.client('cloudformation', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(DOC_DIR,
                                      'Output/aws-UpdateCloudFormationTemplate.json'),
            doc_name=SSM_DOC_NAME,
            doc_type='Automation'
        )

        test_cf_stack = ssm_testing.CFNTester(
            cfn_client=cfn_client,
            template_filename=os.path.abspath(os.path.join(
                DOC_DIR,
                "Tests/CloudFormationTemplates/TestTemplate.yml")),
            stack_name=TEST_CFN_STACK_NAME
        )
        test_cf_stack.create_stack([])

        try:
            user_arn = sts_client.get_caller_identity().get('Arn')

            cleanup_role()
            admin_role = create_role(user_arn)["Role"]["Arn"]
            cleanup_bucket()

            LOGGER.info("Creating automation document")
            self.assertEqual(ssm_doc.create_document(), 'Active')

            role_info = iam_client.get_role_policy(
                RoleName=test_cf_stack.stack_outputs["RoleName"], PolicyName='test-policy-name')
            self.assertEqual(len(role_info["PolicyDocument"]["Statement"]["Action"]), 1)

            LOGGER.info("Creating test S3 bucket")
            s3_client.create_bucket(
                Bucket=TEST_S3_BUCKET,
                CreateBucketConfiguration={
                    "LocationConstraint": "us-west-2"
                }
            )
            s3_client.upload_file(
                os.path.abspath(os.path.join(
                    DOC_DIR,
                    "Tests/CloudFormationTemplates/TestUpdateTemplate.yml")),
                TEST_S3_BUCKET,
                'TestUpdateTemplate.yml')

            update_template = "http://s3-us-west-2.amazonaws.com/{}/TestUpdateTemplate.yml".format(TEST_S3_BUCKET)

            execution = ssm_doc.execute_automation(
                params={'StackNameOrId': [TEST_CFN_STACK_NAME],
                        'TemplateUrl': [update_template],
                        'LambdaAssumeRole': [admin_role],
                        'AutomationAssumeRole': [admin_role]})

            result = ssm_doc.automation_execution_status(ssm_client, execution)

            while test_cf_stack.is_stack_in_status('CREATE_IN_PROGRESS') is True:
                LOGGER.info('Waiting 5 seconds before checking again for document update')
                time.sleep(5)

            self.assertEqual(result, "Success")

            role_info = iam_client.get_role_policy(
                RoleName=test_cf_stack.stack_outputs["RoleName"], PolicyName='test-policy-name')
            self.assertEqual(len(role_info["PolicyDocument"]["Statement"]["Action"]), 3)

        finally:
            try:
                ssm_doc.destroy()
            except Exception:
                pass

            test_cf_stack.delete_stack()

            cleanup_bucket()
            cleanup_role()

