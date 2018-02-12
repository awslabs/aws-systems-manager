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

NEW_INSTANCE_TYPE = 't2.nano'

SSM_DOC_NAME = PREFIX + 'resize-instance'
CFN_STACK_NAME = PREFIX + 'resize-instance'
TEST_CFN_STACK_NAME = PREFIX + 'resize-instance'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

boto3.setup_default_session(region_name=REGION)

iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
sts_client = boto3.client('sts')


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

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(DOC_DIR,
                                      'Output/aws-ResizeInstance.json'),
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

        LOGGER.info('Creating Test Stack')
        LOGGER.info('AMI:' + LINUX_AMI_ID)
        LOGGER.info('Instance Type:' + LINUX_INSTANCE_TYPE)
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
        try:
            LOGGER.info("Creating automation document")
            self.assertEqual(ssm_doc.create_document(), 'Active')

            instance_id = test_cf_stack.stack_outputs['InstanceId']

            execution = ssm_doc.execute_automation(
                params={'InstanceId': [instance_id],
                        'InstanceType': [NEW_INSTANCE_TYPE],
                        'AutomationAssumeRole': [role_arn]})
            self.assertEqual(ssm_doc.automation_execution_status(ssm_client, execution, False), 'Success')

            LOGGER.info('Instance has changed, Verifying instance')

            ec2 = boto3.resource('ec2')
            instance = ec2.Instance(instance_id)

            LOGGER.info("Current instance Type:" + instance.instance_type)

            # Test instance exists in volume
            self.assertEqual(instance.instance_type, NEW_INSTANCE_TYPE)
            self.assertEqual(instance.state.get('Code'), 16)
            LOGGER.info("All Tests Successful, will clean up now")
        finally:
            try:
                ssm_doc.destroy()
            except Exception:
                pass

            test_cf_stack.delete_stack()


if __name__ == '__main__':
    unittest.main()
