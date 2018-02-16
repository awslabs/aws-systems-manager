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

SSM_DOC_NAME = PREFIX + 'delete-snapshot'
CFN_STACK_NAME = PREFIX + 'delete-snapshot'
TEST_CFN_STACK_NAME = PREFIX + 'delete-snapshot'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

boto3.setup_default_session(region_name=REGION)

iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
sts_client = boto3.client('sts')
ec2_client = boto3.client('ec2')


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
    @staticmethod
    def create_snapshot(volume_id):
        ec2 = boto3.resource('ec2')

        description = PREFIX + 'delete-snapshot'
        volume = ec2.Volume(volume_id)
        snapshot = volume.create_snapshot(Description=description)

        return snapshot

    @staticmethod
    def delete_snapshot(snapshot_id):
        try:
            # There shouldn't be anything else in this bucket
            ec2_client.delete_snapshot(
                SnapshotId=snapshot_id
            )
        except Exception:
            pass

    def test_update_document(self):
        cfn_client = boto3.client('cloudformation', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(DOC_DIR,
                                      'Output/aws-DeleteSnapshot.json'),
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
        test_cf_stack.create_stack([
            {
                'ParameterKey': 'UserARN',
                'ParameterValue': sts_client.get_caller_identity().get('Arn')
            }
        ])
        LOGGER.info('Test Stack has been created')

        # Verify role exists
        role_arn = test_cf_stack.stack_outputs['AutomationAssumeRoleARN']
        verify_role_created(role_arn)

        LOGGER.info("Creating automation document")
        self.assertEqual(ssm_doc.create_document(), 'Active')

        volume_id = test_cf_stack.stack_outputs['VolumeId']

        # Now create the snapshot
        snapshot = self.create_snapshot(volume_id)

        try:
            execution = ssm_doc.execute_automation(
                params={'SnapshotId': [snapshot.snapshot_id],
                        'AutomationAssumeRole': [role_arn]})
            self.assertEqual(ssm_doc.automation_execution_status(ssm_client, execution, False), 'Success')

            LOGGER.info('Snapshot is deleted: ' + volume_id)

            snapshot_response = ec2_client.describe_snapshots(
                Filters=[
                    {
                        'Name': 'volume-id',
                        'Values': [volume_id]
                    }
                ]
            )

            # Test instance exists in volume
            snapshots = snapshot_response['Snapshots']

            self.assertEqual(len(snapshots), 0)

            LOGGER.info('Verified snapshot is deleted')
        finally:
            try:
                ssm_doc.destroy()
            except Exception:
                pass

            self.delete_snapshot(snapshot.snapshot_id)

            test_cf_stack.delete_stack()


if __name__ == '__main__':
    unittest.main()

