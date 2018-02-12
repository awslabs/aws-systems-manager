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

SSM_DOC_NAME = PREFIX + 'detach-ebs-volume-mounted'
CFN_STACK_NAME = PREFIX + 'detach-ebs-volume-mounted'
TEST_CFN_STACK_NAME = PREFIX + 'detach-ebs-volume-mounted'

DEVICE_NAME = '/dev/xvdf'

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


def verify_instance_started(instance_id):
    LOGGER.info("Verifying that instance started: " + instance_id)
    # For what ever reason assuming a role that got created too fast fails, so we just wait until we can.
    retry_count = 60
    while True:
        try:
            response = ec2_client.describe_instance_status(InstanceIds=[instance_id])
            instance_status = response['InstanceStatuses'][0]

            # print "Instance State:" + instance_status['InstanceState']['Name'] \
            #       + ", System Status:" + instance_status['SystemStatus']['Status'] \
            #       + ", Instance Status:" + instance_status['InstanceStatus']['Status']

            if instance_status['InstanceStatus']['Status'] == 'ok' \
                    and instance_status['SystemStatus']['Status'] == 'ok':
                break

        except Exception as e:
            retry_count -= 1
            if retry_count == 0:
                raise e

        LOGGER.info("Instance not up... trying again in 10 sec")
        time.sleep(10)


def execute_remote_command(ssm_client, instance_id, commands):
    send_command_response = ssm_client.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={
            'workingDirectory': ['/'],
            'commands': commands,
            'executionTimeout': ['30']
        }
    )

    response = send_command_response['Command']

    command_id = response['CommandId']
    status = response['Status']
    sleep_time = 3
    while status == 'Pending' or status == 'InProgress':
        time.sleep(sleep_time)
        response = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )
        # pprint.pprint(response, indent=2)

        status = response['Status']

    return response


def mount_volume(ssm_client, instance_id, device):
    mounted_directory = 'test_volume'

    LOGGER.info("mounting " + device + " to " + mounted_directory + " on instance " + instance_id)

    commands = [
        'sudo file -s ' + device,
        'sudo mkfs -t ext4 ' + device,
        'sudo mkdir ' + mounted_directory,
        'sudo mount ' + device + ' ' + mounted_directory
    ]

    return execute_remote_command(ssm_client, instance_id, commands)


def unmount_volume(ssm_client, instance_id, device):
    commands = [
        'sudo umount ' + device
    ]

    return execute_remote_command(ssm_client, instance_id, commands)


class DocumentTest(unittest.TestCase):
    def test_update_document(self):
        cfn_client = boto3.client('cloudformation', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(DOC_DIR,
                                      'Output/aws-DetachEBSVolume.json'),
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
                'ParameterKey': 'AMI',
                'ParameterValue': LINUX_AMI_ID
            },
            {
                'ParameterKey': 'INSTANCETYPE',
                'ParameterValue': LINUX_INSTANCE_TYPE
            },
            {
                'ParameterKey': 'DEVICE',
                'ParameterValue': DEVICE_NAME
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

        # Verify instance started
        instance_id = test_cf_stack.stack_outputs['InstanceId']
        verify_instance_started(instance_id)

        LOGGER.info('Mounting Volume')
        # print instance_id
        mount_response = mount_volume(ssm_client, instance_id, DEVICE_NAME)
        # print(mount_response)
        self.assertEqual(mount_response['Status'], 'Success')
        try:
            LOGGER.info("Creating automation document")
            self.assertEqual(ssm_doc.create_document(), 'Active')

            volume_id = test_cf_stack.stack_outputs['VolumeId']

            execution = ssm_doc.execute_automation(
                params={'VolumeId': [volume_id],
                        'AutomationAssumeRole': [role_arn]})
            self.assertEqual(ssm_doc.automation_execution_status(ssm_client, execution, False), 'Failed')

            LOGGER.info('Volume is still attached, now verifying')

            ec2 = boto3.resource('ec2')
            volume = ec2.Volume(volume_id)

            # Test instance exists in volume
            self.assertEqual(len(volume.attachments), 1)

            LOGGER.info('Unmounting volume...')
            unmount_volume(ssm_client, instance_id, DEVICE_NAME)
            time.sleep(10)

            volume.reload()
            LOGGER.info('Verifying is detached')
            self.assertEqual(len(volume.attachments), 0)
            LOGGER.info('Test Successful')
        finally:
            try:
                ssm_doc.destroy()
            except Exception:
                pass

            try:
                unmount_volume(ssm_client, instance_id, DEVICE_NAME)
            except Exception:
                pass

            test_cf_stack.delete_stack()


if __name__ == '__main__':
    unittest.main()
