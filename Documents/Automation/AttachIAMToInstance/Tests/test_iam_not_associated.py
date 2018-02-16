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
import ssm_testing  # noqa pylint: disable=import-error,wrong-import-position

CONFIG = ConfigParser.ConfigParser()
CONFIG.readfp(open(os.path.join(REPOROOT, 'Testing', 'defaults.cfg')))
CONFIG.read([os.path.join(REPOROOT, 'Testing', 'local.cfg')])

REGION = CONFIG.get('general', 'region')
PREFIX = CONFIG.get('general', 'resource_prefix')

WINDOWS_AMI_ID = CONFIG.get('windows', 'windows2016.{}'.format(REGION))
INSTANCE_TYPE = CONFIG.get('windows', 'instance_type')
LINUX_AMI_ID = CONFIG.get('linux', 'ami')
LINUX_INSTANCE_TYPE = CONFIG.get('linux', 'instance_type')

SSM_DOC_NAME = PREFIX + 'attach-iam-instance-no-assoc'
CFN_STACK_NAME = PREFIX + 'attach-iam-instance-no-assoc'
TEST_CFN_STACK_NAME = PREFIX + 'attach-iam-instance-no-assoc'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

boto3.setup_default_session(region_name=REGION)

iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
sts_client = boto3.client('sts')
ec2_client = boto3.client('ec2')


def disassociate_iam_instance_profile(association_id):
    return ec2_client.disassociate_iam_instance_profile(
        AssociationId=association_id
    )


def remove_role_from_instance_profile(profile_name, role_name):
    return iam_client.remove_role_from_instance_profile(
        InstanceProfileName=profile_name,
        RoleName=role_name
    )


def delete_instance_profile(profile_name):
    return iam_client.delete_instance_profile(
        InstanceProfileName=profile_name
    )


def verify_role_created(role_arn):
    LOGGER.info("Verifying that role exists: " + role_arn)
    # For what ever reason assuming a role that got created too fast fails, so we just wait until we can.
    retry_count = 12
    while True:
        try:
            sts_client.assume_role(RoleArn=role_arn, RoleSessionName="checking_assume")
            break
        except Exception as e:
            retry_count -= 1
            if retry_count == 0:
                raise e

            LOGGER.info("Unable to assume role... trying again in 5 sec")
            time.sleep(5)


class DocumentTest(unittest.TestCase):
    def test_update_document(self):
        cfn_client = boto3.client('cloudformation', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        test_cf_stack = ssm_testing.CFNTester(
            cfn_client=cfn_client,
            template_filename=os.path.abspath(os.path.join(
                DOC_DIR,
                "Tests/CloudFormationTemplates/TestNotAssociated.yml")),
            stack_name=TEST_CFN_STACK_NAME
        )

        LOGGER.info('Creating Test Stack')
        test_cf_stack.create_stack([
            {
                'ParameterKey': 'AMI',
                'ParameterValue': LINUX_AMI_ID
            },
            {
                'ParameterKey': 'INSTANCETYPE',
                'ParameterValue': LINUX_INSTANCE_TYPE
            },
            {
                'ParameterKey': 'UserARN',
                'ParameterValue': sts_client.get_caller_identity().get('Arn')
            }
        ])
        LOGGER.info('Test Stack has been created')

        # Verify role exists
        role_arn = test_cf_stack.stack_outputs['AutomationAssumeRoleARN']
        verify_role_created(role_arn)

        # Crete the lambda
        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(DOC_DIR,
                                      'Output/aws-AttachIAMToInstance.json'),
            doc_name=SSM_DOC_NAME,
            doc_type='Automation'
        )

        LOGGER.info("Creating automation document")
        self.assertEqual(ssm_doc.create_document(), 'Active')

        try:
            instance_id = test_cf_stack.stack_outputs['InstanceId']
            role_name = test_cf_stack.stack_outputs['AutomationAssumeRoleName']

            execution = ssm_doc.execute_automation(
                params={'InstanceId': [instance_id],
                        'RoleName': [role_name],
                        'AutomationAssumeRole': [role_arn]})
            self.assertEqual(ssm_doc.automation_execution_status(ssm_client, execution, False), 'Success')

            LOGGER.info('automation executed successfully')
            response = ssm_client.get_automation_execution(AutomationExecutionId=execution)
            str_payload = response['AutomationExecution']['Outputs']['attachIAMToInstance.Payload'][0]
            payload = json.loads(str_payload)
            association_id = payload['AssociationId']
            profile_name = payload['InstanceProfileName']

            self.assertEqual(role_name, payload['RoleName'])

            LOGGER.info('Verify that the instance has a profile')
            profile_instance_response = ec2_client.describe_iam_instance_profile_associations(Filters=[{
                'Name': 'instance-id',
                'Values': [instance_id]
            }])
            self.assertEqual(len(profile_instance_response['IamInstanceProfileAssociations']), 1)
            iam_instance_profile_association = profile_instance_response['IamInstanceProfileAssociations'][0]
            self.assertEqual(len(profile_instance_response['IamInstanceProfileAssociations']), 1)
            self.assertEqual(iam_instance_profile_association['AssociationId'], association_id)
            self.assertEqual(iam_instance_profile_association['InstanceId'], instance_id)

            LOGGER.info('Verify that the instance profile has the role')
            instance_profile_response = iam_client.get_instance_profile(
                InstanceProfileName=profile_name
            )
            self.assertEqual(instance_profile_response['InstanceProfile']['InstanceProfileName'], profile_name)

            role_count = 0
            for role in instance_profile_response['InstanceProfile']['Roles']:
                if role['RoleName'] == role_name:
                    role_count += 1

            self.assertEqual(role_count, 1)

            LOGGER.info('Tests successful. Cleaning up')
            remove_role_from_instance_profile(profile_name, role_name)
            delete_instance_profile(profile_name)
            disassociate_iam_instance_profile(association_id)

            LOGGER.info('Clean up successful')
        finally:
            try:
                ssm_doc.destroy()
            except Exception:
                pass

            test_cf_stack.delete_stack()


if __name__ == '__main__':
    unittest.main()

