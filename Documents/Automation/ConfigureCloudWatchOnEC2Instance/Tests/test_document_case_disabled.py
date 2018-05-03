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
import ssm_testing  # noqa pylint: disable=import-error,wrong-import-position

CONFIG = ConfigParser.ConfigParser()
CONFIG.readfp(open(os.path.join(REPOROOT, 'Testing', 'defaults.cfg')))
CONFIG.read([os.path.join(REPOROOT, 'Testing', 'local.cfg')])

REGION = CONFIG.get('general', 'region')
PREFIX = CONFIG.get('general', 'resource_prefix')
AMIID = CONFIG.get('linux', 'ami')
INSTANCETYPE = CONFIG.get('linux', 'instance_type')
SSM_DOC_NAME = PREFIX + 'config-cw-on-instance'
CFN_STACK_NAME = PREFIX + 'config-cw-on-instance'
TEST_CFN_STACK_NAME = PREFIX + 'config-cw-on-instance'
MONITOR_STATE = 'Disabled'
REQUIRED_ENDSTATE = 'disabled'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

boto3.setup_default_session(region_name=REGION)
ec2_client = boto3.client('ec2', region_name=REGION)
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


def verify_monitorstate_changed(instance_id):
    LOGGER.info("Verifying that test subject EC-2 instance's monitoring state has changed")

    while True:
        instance_description = ec2_client.describe_instances(InstanceIds=[instance_id])
        current_state = instance_description['Reservations'][0]['Instances'][0]['Monitoring']['State']
        if current_state == REQUIRED_ENDSTATE:
            LOGGER.info("Monitoring change reached fruition!")
            return REQUIRED_ENDSTATE
        else:
            LOGGER.info("InstanceMonitoring State hasn't changed yet ("+current_state+")... trying again in 5 sec")
            time.sleep(5)


class DocumentTest(unittest.TestCase):
    def test_update_document(self):
        LOGGER.info("TESTING Automation Document DISABLE Case")
        cfn_client = boto3.client('cloudformation', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(
                DOC_DIR,
                'Output/aws-ConfigureCloudWatchOnEC2Instance.json'),
            doc_name=SSM_DOC_NAME,
            doc_type='Automation'
        )

        test_cf_stack = ssm_testing.CFNTester(
            cfn_client=cfn_client,
            template_filename=os.path.join(
                DOC_DIR,
                'Tests/CloudFormationTemplates/TestTemplate.yml'),
            stack_name=TEST_CFN_STACK_NAME
        )

        LOGGER.info('Creating Test Stack')
        test_cf_stack.create_stack([
            {
                'ParameterKey': 'UserARN',
                'ParameterValue': sts_client.get_caller_identity().get('Arn')
            },
            {
                'ParameterKey': 'AMI',
                'ParameterValue': AMIID
            },
            {
                'ParameterKey': 'INSTANCETYPE',
                'ParameterValue': INSTANCETYPE
            }
        ])
        LOGGER.info('Test Stack has been created')
        LOGGER.info(test_cf_stack)
        # Verify role exists
        role_arn = test_cf_stack.stack_outputs['AutomationAssumeRoleARN']
        verify_role_created(role_arn)

        LOGGER.info('Creating automation document')
        self.assertEqual(ssm_doc.create_document(), 'Active')

        ec2_instance_id = test_cf_stack.stack_outputs['InstanceId']
        LOGGER.info('EC-2 instance spun up, id = ' + ec2_instance_id)

        try:
            LOGGER.info('Running the Automation-Document now!')

            execution = ssm_doc.execute_automation(
                params={
                    'InstanceId': [ec2_instance_id],
                    'status': [MONITOR_STATE],
                    'AutomationAssumeRole': [role_arn]
                })
            self.assertEqual(ssm_doc.automation_execution_status(ssm_client, execution, False), 'Success')
            LOGGER.info('Automation-Execution was successful!')

            end_state = verify_monitorstate_changed(ec2_instance_id)
            LOGGER.info('test subject host Monitoring state is ' + end_state)

            self.assertEqual(end_state, REQUIRED_ENDSTATE, "The EC-2 instance monitoring failed to change to disabled")
            LOGGER.info('End of Disable Case Test')
        finally:
            try:
                ssm_doc.destroy()
            except Exception:
                pass

            test_cf_stack.delete_stack()

if __name__ == '__main__':
    unittest.main()
