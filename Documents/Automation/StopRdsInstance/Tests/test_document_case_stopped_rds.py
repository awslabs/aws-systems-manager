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
SERVICE_ROLE_NAME = CONFIG.get('general', 'automation_service_role_name')

SSM_DOC_NAME = PREFIX + 'stop-stopped-rds-instance'
CFN_STACK_NAME = PREFIX + 'stop-stopped-rds-instance'
TEST_CFN_STACK_NAME = PREFIX + 'stop-stopped-rds-instance'
TEST_DB_CLASS = 'db.m1.small'
TEST_DB_ALLOCATED_STORAGE = '20'
TEST_DB_ENGINE = 'mysql'
TEST_DB_MASTER_USERNAME = 'test_root'
TEST_DB_MASTER_USER_PASSWORD = 'Password123'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

boto3.setup_default_session(region_name=REGION)

rds_client = boto3.client('rds')
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


def verify_db_stopped(db_instance_id):
    is_stopped = False
    while is_stopped is False:
        LOGGER.info('Waiting 10 seconds before checking again for successful DB stop completion')
        time.sleep(10)

        db_state = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)

        if db_state['DBInstances'][0]['DBInstanceStatus'] == 'stopped':
            is_stopped = True

    return True


class DocumentTest(unittest.TestCase):
    def test_update_document(self):
        cfn_client = boto3.client('cloudformation', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(DOC_DIR, 'Output/aws-StopRdsInstance.json'),
            doc_name=SSM_DOC_NAME,
            doc_type='Automation'
        )

        test_cf_stack = ssm_testing.CFNTester(
            cfn_client=cfn_client,
            template_filename=os.path.join(DOC_DIR, 'Tests/CloudFormationTemplates/TestTemplate.yml'),
            stack_name=TEST_CFN_STACK_NAME
        )

        LOGGER.info('Creating Test Stack')
        test_cf_stack.create_stack([
            {
                'ParameterKey': 'UserARN',
                'ParameterValue': sts_client.get_caller_identity().get('Arn')
            },
            {
                'ParameterKey': 'DBInstanceClass',
                'ParameterValue': TEST_DB_CLASS
            },
            {
                'ParameterKey': 'AllocatedStorage',
                'ParameterValue': TEST_DB_ALLOCATED_STORAGE
            },
            {
                'ParameterKey': 'Engine',
                'ParameterValue': TEST_DB_ENGINE
            },
            {
                'ParameterKey': 'MasterUsername',
                'ParameterValue': TEST_DB_MASTER_USERNAME
            },
            {
                'ParameterKey': 'MasterUserPassword',
                'ParameterValue': TEST_DB_MASTER_USER_PASSWORD
            }
        ])
        LOGGER.info('Test Stack has been created')

        # Verify role exists
        role_arn = test_cf_stack.stack_outputs['AutomationAssumeRoleARN']
        verify_role_created(role_arn)

        # Start an Rds instance for us to stop
        LOGGER.info('Creating automation document')
        self.assertEqual(ssm_doc.create_document(), 'Active')

        db_instance_id = test_cf_stack.stack_outputs['InstanceId']
        LOGGER.info("Test Case DB Instance ID:" + db_instance_id)

        rds_client.stop_db_instance(DBInstanceIdentifier=db_instance_id)
        # ...waiting for the stop to complete, then proceeding. We're procedurally stopping the DB so that we can prove
        # the Automation Under Test won't implode under legit edge cases (like a logical noop case)
        verify_db_stopped(db_instance_id)

        try:
            LOGGER.info('Executing SSM automation document to stop instances')
            # Stop the Rds instance
            execution = ssm_doc.execute_automation(
                params={'InstanceId': [db_instance_id],
                        'AutomationAssumeRole': [role_arn]})
            self.assertEqual(ssm_doc.automation_execution_status(ssm_client, execution, False), 'Success')

            # Now obtain evidence to prove the Rds instance has stopped
            db_state = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
            self.assertEqual(db_state['DBInstances'][0]['DBInstanceStatus'], "stopped")

            LOGGER.info('Verified the DB instance is stopped')
        finally:
            try:
                ssm_doc.destroy()
            except Exception:
                pass

            test_cf_stack.delete_stack()


if __name__ == '__main__':
    unittest.main()
