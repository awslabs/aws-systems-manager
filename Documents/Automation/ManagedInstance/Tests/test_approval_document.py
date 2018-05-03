import os
import sys
import logging
import unittest

import ConfigParser
import boto3
import json
import mock

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
import managedinstanceutil as util

CONFIG = ConfigParser.ConfigParser()
CONFIG.readfp(open(os.path.join(REPOROOT, 'Testing', 'defaults.cfg')))
CONFIG.read([os.path.join(REPOROOT, 'Testing', 'local.cfg')])

REGION = CONFIG.get('general', 'region')
PREFIX = CONFIG.get('general', 'resource_prefix')
SERVICE_ROLE_NAME = CONFIG.get('general', 'automation_service_role_name')

WINDOWS_AMI_ID = CONFIG.get('windows', 'windows2016.{}'.format(REGION))
LINUX_AMI_ID = CONFIG.get('linux', 'ami')
INSTANCE_TYPE = CONFIG.get('windows', 'instance_type')

SSM_DOC_NAME = PREFIX + 'managed-instance-w-approval'
CFN_STACK_NAME = PREFIX + 'managed-instance-w-approval'
APPROVAL_TOPIC = PREFIX + 'managed-instance-w-approval-topic'
LAMBDA_ROLE = PREFIX + 'managed-instance-w-approval-lambda-role'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

boto3.setup_default_session(region_name=REGION)

ec2_client = boto3.client('ec2')
as_client = boto3.client('autoscaling')
iam_client = boto3.client('iam')
ssm_client = boto3.client('ssm')
sns_client = boto3.client('sns')
sts_client = boto3.client('sts')

KEY_PAIR_NAME = PREFIX + 'keypair'
GROUP_NAME = PREFIX + "test-group-name"
PROFILE_NAME = PREFIX + "test-profile-name"


def cleanup(vpc_id):
    instances = ec2_client.describe_instances(
        Filters=[{'Name': 'tag:aws:cloudformation:stack-name', 'Values': [CFN_STACK_NAME]}])
    for reservation in instances["Reservations"]:
        for instance in reservation["Instances"]:
            util.cleanup_instance(ec2_client, instance["InstanceId"])

    util.cleanup_security_groups(ec2_client, vpc_id, GROUP_NAME)
    util.cleanup_instance_profile(iam_client, PROFILE_NAME)
    util.cleanup_key_pair(ec2_client, KEY_PAIR_NAME)


class TestApprovalDocument(unittest.TestCase):
    def execute(self, ami, document, custom_prefix):
        default_vpc = util.find_default_vpc(ec2_client)
        self.assertIsNotNone(default_vpc["VpcId"])
        user_arn = boto3.client('sts', region_name=REGION).get_caller_identity().get('Arn')

        ssm_doc = None
        with util.sns_topic(APPROVAL_TOPIC, sns_client) as sns_topic, \
                util.admin_role(iam_client, sts_client, custom_prefix + LAMBDA_ROLE, user_arn) as admin_role:
            sns_topic_arn = sns_topic["TopicArn"]
            admin_role_arn = admin_role["Role"]["Arn"]

            try:
                cleanup(default_vpc["VpcId"])

                ssm_doc = ssm_testing.SSMTester(
                    ssm_client=ssm_client,
                    doc_filename=os.path.join(
                        DOC_DIR,
                        'Output',
                        document),
                    doc_name=SSM_DOC_NAME,
                    doc_type='Automation'
                )

                ec2_client.create_key_pair(
                    KeyName=KEY_PAIR_NAME
                )

                self.assertEqual(ssm_doc.create_document(), 'Active')

                execution = ssm_doc.execute_automation(
                    params={
                        'AmiId': [ami],
                        'KeyPairName': [KEY_PAIR_NAME],
                        'AutomationAssumeRole': [admin_role_arn],
                        'InstanceType': [INSTANCE_TYPE],
                        'StackName': [CFN_STACK_NAME],
                        'RemoteAccessCidr': ["10.0.0.0/24"],
                        'Approvers': [user_arn],
                        'SNSTopicArn': [sns_topic_arn],
                        'RoleName': [PROFILE_NAME],
                        'GroupName': [GROUP_NAME]})
                self.assertEqual(ssm_doc.automation_execution_status(ssm_client, execution, False), 'Waiting')

                LOGGER.info('Approving continuation of execution')
                ssm_client.send_automation_signal(
                    AutomationExecutionId=execution,
                    SignalType='Approve'
                )

                result = ssm_doc.automation_execution_status(ssm_client, execution)

                self.assertEqual(result, "Success")

                instances = ec2_client.describe_instances(
                    Filters=[
                        {'Name': 'tag:aws:cloudformation:stack-name', 'Values': [CFN_STACK_NAME]},
                        {'Name': 'instance-state-name', 'Values': ["running"]}
                    ])
                running_instances = []
                for reservation in instances["Reservations"]:
                    for instance in reservation["Instances"]:
                        print instance
                        running_instances.append(instance["InstanceId"])

                        self.assertEqual(instance["VpcId"], default_vpc["VpcId"])
                        self.assertEqual(instance["KeyName"], KEY_PAIR_NAME)
                        self.assertGreater(len(instance["SecurityGroups"]), 0)
                        self.assertEqual(instance["SecurityGroups"][0]["GroupName"], GROUP_NAME)
                        self.assertEqual(instance["InstanceType"], INSTANCE_TYPE)
                        self.assertTrue(instance["IamInstanceProfile"]["Arn"].endswith(PROFILE_NAME))
                        self.assertEqual(instance["State"]["Name"], "running")

                ssm_info = ssm_client.describe_instance_information(
                    InstanceInformationFilterList=[{
                        'key': 'InstanceIds',
                        'valueSet': running_instances
                    }]
                )
                print ssm_info

            finally:
                cleanup(default_vpc["VpcId"])
                if ssm_doc is not None:
                    ssm_doc.destroy()

    def test_windows_document(self):
        self.execute(WINDOWS_AMI_ID, "aws-CreateManagedWindowsInstanceWithApproval.json", "windows-")

    def test_linux_document(self):
        self.execute(LINUX_AMI_ID, "aws-CreateManagedLinuxInstanceWithApproval.json", "linux-")
