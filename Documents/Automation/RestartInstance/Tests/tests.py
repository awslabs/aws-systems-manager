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
AMIID = CONFIG.get('linux', 'ami')
SERVICE_ROLE_NAME = CONFIG.get('general', 'automation_service_role_name')
INSTANCE_TYPE = CONFIG.get('linux', 'instance_type')
SSM_DOC_NAME = PREFIX + 'automation-restartinstance'
INSTANCE_CFN_STACKNAME = PREFIX + 'automation-restartinstance'

if CONFIG.get('general', 'log_level') == 'warn':
    logging.basicConfig(level=logging.WARN)
elif CONFIG.get('general', 'log_level') == 'info':
    logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class TestCase(unittest.TestCase):
    """Main test class for SSM document."""

    @staticmethod
    def test_jsonlinting():
        """Verify correct json syntax."""
        for i in glob.glob(os.path.join(DOC_DIR, 'Documents', '*.json')):
            assert demjson.jsonlint('jsonlint').main([i]) == 0, (
                'SSM Autmation JSON documents are not well formed')
        for i in glob.glob(os.path.join(DOC_DIR, 'Tests', 'CloudFormationTemplates' '*.json')):
            assert demjson.jsonlint('jsonlint').main([i]) == 0, (
                'CF Template JSON documents are not well formed')

    @staticmethod
    def testdocument():
        """Verify correct deployment and use of document."""
        cfn_client = boto3.client('cloudformation', region_name=REGION)
        ec2_client = boto3.client('ec2', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(DOC_DIR,
                                      'Documents',
                                      'aws-RestartEC2Instance.json'),
            doc_name=SSM_DOC_NAME,
            doc_type='Automation'
        )

        test_cf_stack = ssm_testing.CFNTester(
            cfn_client=cfn_client,
            template_filename=os.path.join(DOC_DIR,
                                           'Tests',
                                           'CloudFormationTemplates',
                                           'TwoInstances.yml'),
            stack_name=INSTANCE_CFN_STACKNAME
        )

        automation_role = ssm_doc.get_automation_role(
            boto3.client('sts', region_name=REGION),
            boto3.client('iam', region_name=REGION),
            SERVICE_ROLE_NAME
        )

        LOGGER.info('Starting instances for testing')
        test_cf_stack.create_stack([
            {
                'ParameterKey': 'AMI',
                'ParameterValue': AMIID
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

            LOGGER.info('Running automation to restart multiple instances '
                        '(using defined role)')
            instances_1_2 = [test_cf_stack.stack_outputs['Instance0Id'],
                             test_cf_stack.stack_outputs['Instance1Id']]
            execution = ssm_doc.execute_automation(
                params={'InstanceId': instances_1_2,
                        'AutomationAssumeRole': [automation_role]})

            LOGGER.info('Verifying automation executions have concluded successfully')

            assert ssm_doc.automation_execution_status(
                ssm_client,
                execution
            ) == 'Success', 'Instances not restarted successfully'

            LOGGER.info('Verifying all instances are running')
            describe_res = ec2_client.describe_instance_status(
                InstanceIds=instances_1_2,
                IncludeAllInstances=True
            )
            assert all(d['InstanceState']['Name'] == 'running' for d in describe_res['InstanceStatuses']) is True, (  # noqa pylint: disable=line-too-long
                'Instances not started')

        finally:
            test_cf_stack.delete_stack()
            ssm_doc.destroy()


if __name__ == '__main__':
    unittest.main()
