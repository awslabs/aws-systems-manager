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
"""Main test file for SSM document."""

import ConfigParser
import glob
import logging
import os
import sys
import unittest

import boto3
import demjson

DOC_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPO_ROOT = os.path.dirname(DOC_DIR)

# Import shared testing code
sys.path.append(
    os.path.join(
        REPO_ROOT,
        'Testing'
    )
)
import ssm_testing  # noqa pylint: disable=import-error,wrong-import-position

CONFIG = ConfigParser.ConfigParser()
CONFIG.readfp(open(os.path.join(REPO_ROOT, 'Testing', 'defaults.cfg')))
CONFIG.read([os.path.join(REPO_ROOT, 'Testing', 'local.cfg')])

REGION = CONFIG.get('general', 'region')
PREFIX = CONFIG.get('general', 'resource_prefix')
AMI_ID = CONFIG.get('linux', 'ami')
SERVICE_ROLE_NAME = CONFIG.get('general', 'automation_service_role_name')
INSTANCE_TYPE = CONFIG.get('linux', 'instance_type')
SSM_DOC_NAME = PREFIX + 'automation-delete-cf-stack'
INSTANCE_CFN_STACK_NAME = PREFIX + 'automation-delete-cf-stack'

if CONFIG.get('general', 'log_level') == 'warn':
    logging.basicConfig(level=logging.WARN)
elif CONFIG.get('general', 'log_level') == 'info':
    logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

cfn_client = boto3.client('cloudformation', region_name=REGION)
ec2_client = boto3.client('ec2', region_name=REGION)
ssm_client = boto3.client('ssm', region_name=REGION)
sts_client = boto3.client('sts', region_name=REGION)
iam_client = boto3.client('iam', region_name=REGION)


class TestCase(unittest.TestCase):
    """Main test class for SSM document."""

    @staticmethod
    def test_jsonlinting():
        """Verify correct json syntax."""
        for i in glob.glob(os.path.join(DOC_DIR, 'Documents', '*.json')):
            assert demjson.jsonlint('jsonlint').main([i]) == 0, (
                'SSM Autmation JSON documents are not well formed')

    @staticmethod
    def test_document():
        """Verify correct deployment and use of document."""

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(DOC_DIR,
                                      'Documents',
                                      'aws-DeleteCloudFormation.json'),
            doc_name=SSM_DOC_NAME,
            doc_type='Automation'
        )

        test_cf_stack = ssm_testing.CFNTester(
            cfn_client=cfn_client,
            template_filename=os.path.join(DOC_DIR,
                                           'Tests',
                                           'CloudFormationTemplates',
                                           'TwoInstances.yml'),
            stack_name=INSTANCE_CFN_STACK_NAME
        )

        automation_role = ssm_doc.get_automation_role(sts_client, iam_client, SERVICE_ROLE_NAME)

        LOGGER.info('Starting instances for testing')
        stack = test_cf_stack.create_stack([
            {
                'ParameterKey': 'AMI',
                'ParameterValue': AMI_ID
            },
            {
                'ParameterKey': 'INSTANCETYPE',
                'ParameterValue': INSTANCE_TYPE
            }
        ])

        try:
            LOGGER.info('Creating automation document')
            assert ssm_doc.create_document() == 'Active', ('Document not '
                                                           'created '
                                                           'successfully')

            execution = ssm_doc.execute_automation(params={'StackNameOrId': [INSTANCE_CFN_STACK_NAME],
                                                           'AutomationAssumeRole': [automation_role]})

            LOGGER.info('Verifying automation executions have concluded successfully')

            assert ssm_doc.automation_execution_status(
                ssm_client,
                execution
            ) == 'Success', 'Stack not deleted correctly'

            LOGGER.info('Verifying stack is deleted')
            # deleted stacks require the Stack ID, not the name, as the param to describe_stacks
            stack_desc = cfn_client.describe_stacks(StackName=stack['StackId'])
            stack_status = stack_desc['Stacks'][0]['StackStatus']
            assert stack_status == 'DELETE_COMPLETE', \
                'Stack deletion failed with status: ' + stack_status

        finally:
            ssm_doc.destroy()


if __name__ == '__main__':
    unittest.main()

