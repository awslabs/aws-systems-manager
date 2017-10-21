#!/usr/bin/env python
"""Main test file for Stop Instances SSM document."""

import ConfigParser
import glob
import logging
import os
import sys
import unittest

import boto3
import demjson

DOCDIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPOROOT = os.path.dirname(DOCDIR)

# Import shared testing code
sys.path.append(
    os.path.join(
        REPOROOT,
        'testing'
    )
)
import ssm_testing  # noqa pylint: disable=import-error,wrong-import-position

CONFIG = ConfigParser.ConfigParser()
CONFIG.readfp(open(os.path.join(REPOROOT, 'testing', 'defaults.cfg')))
CONFIG.read([os.path.join(REPOROOT, 'testing', 'local.cfg')])

REGION = CONFIG.get('general', 'region')
PREFIX = CONFIG.get('general', 'resource_prefix')
AMIID = CONFIG.get('linux', 'ami')
SERVICEROLENAME = CONFIG.get('general', 'automation_service_role_name')
INSTANCETYPE = CONFIG.get('linux', 'instance_type')
SSMDOCNAME = PREFIX + 'automation-stopinstance'
INSTANCECFNSTACKNAME = PREFIX + 'automation-stopinstance'

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
        for i in glob.glob(os.path.join(DOCDIR, 'Documents', '*.json')):
            assert demjson.jsonlint('jsonlint').main([i]) == 0, (
                'JSON documents are not well formed')

    """"\
    Test approach:
        Create CF (CloudFormation) template
        Run CF template, which will start 2 EC2 instances
        Ensure CF template has successfully executed and that the EC2 instances are currently running
        Create the SSM Automation document
        Ensure Automation document is created successfully
        Execute automation document (which will stop the specified EC2 instances)
        Verify EC2 instances are in stopped state
        Teardown CF and delete automation doc
    """
    @staticmethod
    def testdocument():
        """Verify correct deployment and use of document."""
        cfn_client = boto3.client('cloudformation', region_name=REGION)
        ec2_client = boto3.client('ec2', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(DOCDIR,
                                      'Documents',
                                      'aws-StopEC2Instance.json'),
            doc_name=SSMDOCNAME,
            doc_type='Automation'
        )

        test_cf_stack = ssm_testing.CFNTester(
            cfn_client=cfn_client,
            template_filename=os.path.join(DOCDIR,
                                           'Tests',
                                           'CloudFormationTemplates',
                                           'TwoInstances.json'),
            stack_name=INSTANCECFNSTACKNAME
        )

        automation_role = ssm_doc.get_automation_role(
            boto3.client('sts', region_name=REGION),
            boto3.client('iam', region_name=REGION),
            SERVICEROLENAME
        )

        LOGGER.info('Starting 2 instances for testing')
        test_cf_stack.create_stack([
            {
                'ParameterKey': 'AMI',
                'ParameterValue': AMIID
            },
            {
                'ParameterKey': 'INSTANCETYPE',
                'ParameterValue': INSTANCETYPE
            }
        ])
        try:
            LOGGER.info('Creating automation document')
            assert ssm_doc.create_document() == 'Active', ('Document not '
                                                           'created '
                                                           'successfully')

            LOGGER.info('Running automation to stop multiple instances '
                        '(using defined role)')
            instances_1_2 = [test_cf_stack.stack_outputs['Instance0Id'],
                             test_cf_stack.stack_outputs['Instance1Id']]

            LOGGER.info('Verifying all instances are running')
            describe_res = ec2_client.describe_instance_status(
                InstanceIds=[
                    x for x in test_cf_stack.stack_outputs.itervalues()
                ],
                IncludeAllInstances=True
            )
            assert all(d['InstanceState']['Name'] == 'running' for d in describe_res['InstanceStatuses']) is True, (  # noqa pylint: disable=line-too-long
                'Instances not started')

            LOGGER.info("Executing SSM automation document to stop instances")
            execution = ssm_doc.execute_automation(
                params={'InstanceIds': instances_1_2,
                        'AutomationAssumeRole': [automation_role]})

            LOGGER.info('Verifying automation executions have concluded '
                        'successfully')

            LOGGER.info('Ensuring instances have stopped')
            ssm_doc.ensure_no_instance_in_state(
                ec2_client,
                'stopping',
                [x for x in test_cf_stack.stack_outputs.itervalues()])

            assert ssm_doc.automation_execution_status(
                ssm_client,
                execution
            ) == 'Success', 'Instance not started'

            LOGGER.info("Executing SSM automation document to stop instances")
            execution = ssm_doc.execute_automation(
                params={'InstanceIds': instances_1_2,
                        'AutomationAssumeRole': [automation_role]})

            LOGGER.info('Verifying automation executions have concluded '
                        'successfully')

            LOGGER.info('Ensuring instances have stopped')
            ssm_doc.ensure_no_instance_in_state(
                ec2_client,
                'stopping',
                [x for x in test_cf_stack.stack_outputs.itervalues()])

            assert ssm_doc.automation_execution_status(
                ssm_client,
                execution
            ) == 'Success', 'Instance not started'

        finally:
            test_cf_stack.delete_stack()
            ssm_doc.destroy()


if __name__ == '__main__':
    unittest.main()
