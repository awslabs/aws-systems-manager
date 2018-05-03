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

SSM_DOC_NAME = PREFIX + 'managed-instance'
CFN_STACK_NAME = PREFIX + 'managed-instance'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

boto3.setup_default_session(region_name=REGION)

ec2 = boto3.resource('ec2')

ec2_client = boto3.client('ec2')
as_client = boto3.client('autoscaling')
iam_client = boto3.client('iam')
ssm_client = boto3.client('ssm')

KEY_PAIR_NAME = PREFIX + 'keypair'
GROUP_NAME = PREFIX + "test-group-name"
PROFILE_NAME = PREFIX + "test-profile-name"


def create_custom_vpc():
    vpc_result = ec2_client.describe_vpcs(
        Filters=[{
            'Name': 'tag:scope',
            'Values': ['testing']
        }]
    )
    if len(vpc_result["Vpcs"]) > 0:
        return vpc_result["Vpcs"][0]
    else:
        result = ec2_client.create_vpc(CidrBlock="10.0.0.0/24")

        exists_waiter = ec2_client.get_waiter('vpc_exists')
        exists_waiter.wait(VpcIds=[result["Vpc"]["VpcId"]])

        available_waiter = ec2_client.get_waiter('vpc_available')
        available_waiter.wait(VpcIds=[result["Vpc"]["VpcId"]])

        vpc = result["Vpc"]
        vpc_client = ec2.Vpc(result["Vpc"]["VpcId"])
        vpc_client.create_tags(
            Tags=[{
                'Key': 'scope',
                'Value': 'testing'
            }]
        )

        return vpc


def create_custom_security_group(vpc_id):
    subnet_result = ec2_client.describe_subnets(
        Filters=[{
            'Name': 'tag:scope',
            'Values': ['testing']
        }]
    )
    if len(subnet_result["Subnets"]) > 0:
        return ec2.Subnet(subnet_result["Subnets"][0]["SubnetId"])
    else:
        result = ec2.create_subnet(CidrBlock="10.0.0.0/24", VpcId=vpc_id)

        available_waiter = ec2_client.get_waiter('subnet_available')
        available_waiter.wait(SubnetIds=[result.id])

        result.create_tags(
            Tags=[{
                'Key': 'scope',
                'Value': 'testing'
            }]
        )

        return result


def cleanup(vpc_id):
    instances = ec2_client.describe_instances(
        Filters=[{'Name': 'tag:aws:cloudformation:stack-name', 'Values': [CFN_STACK_NAME]}])
    for reservation in instances["Reservations"]:
        for instance in reservation["Instances"]:
            util.cleanup_instance(ec2_client, instance["InstanceId"])

    util.cleanup_security_groups(ec2_client, vpc_id, GROUP_NAME)
    util.cleanup_instance_profile(iam_client, PROFILE_NAME)
    util.cleanup_key_pair(ec2_client, KEY_PAIR_NAME)


class TestDocument(unittest.TestCase):
    def test_windows_documnent(self):
        default_vpc = util.find_default_vpc(ec2_client)
        self.assertIsNotNone(default_vpc["VpcId"])

        try:
            cleanup(default_vpc["VpcId"])

            ssm_doc = ssm_testing.SSMTester(
                ssm_client=ssm_client,
                doc_filename=os.path.join(
                    DOC_DIR,
                    'Output',
                    'aws-CreateManagedWindowsInstance.json'),
                doc_name=SSM_DOC_NAME,
                doc_type='Automation'
            )

            automation_role = ssm_doc.get_automation_role(
                boto3.client('sts', region_name=REGION),
                boto3.client('iam', region_name=REGION),
                SERVICE_ROLE_NAME
            )

            ec2_client.create_key_pair(
                KeyName=KEY_PAIR_NAME
            )

            self.assertEqual(ssm_doc.create_document(), 'Active')

            execution = ssm_doc.execute_automation(
                params={
                    'AmiId': [WINDOWS_AMI_ID],
                    'KeyPairName': [KEY_PAIR_NAME],
                    'AutomationAssumeRole': [automation_role],
                    'InstanceType': [INSTANCE_TYPE],
                    'StackName': [CFN_STACK_NAME],
                    'RemoteAccessCidr': ["10.0.0.0/24"],
                    'RoleName': [PROFILE_NAME],
                    'GroupName': [GROUP_NAME]})

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

    def test_linux_document(self):
        default_vpc = util.find_default_vpc(ec2_client)
        self.assertIsNotNone(default_vpc["VpcId"])

        ssm_doc = None
        try:
            cleanup(default_vpc["VpcId"])

            ssm_doc = ssm_testing.SSMTester(
                ssm_client=ssm_client,
                doc_filename=os.path.join(
                    DOC_DIR,
                    'Output',
                    'aws-CreateManagedLinuxInstance.json'),
                doc_name=SSM_DOC_NAME,
                doc_type='Automation'
            )

            automation_role = ssm_doc.get_automation_role(
                boto3.client('sts', region_name=REGION),
                boto3.client('iam', region_name=REGION),
                SERVICE_ROLE_NAME
            )

            ec2_client.create_key_pair(
                KeyName=KEY_PAIR_NAME
            )

            self.assertEqual(ssm_doc.create_document(), 'Active')

            execution = ssm_doc.execute_automation(
                params={
                    'AmiId': [LINUX_AMI_ID],
                    'KeyPairName': [KEY_PAIR_NAME],
                    'AutomationAssumeRole': [automation_role],
                    'InstanceType': [INSTANCE_TYPE],
                    'StackName': [CFN_STACK_NAME],
                    'RemoteAccessCidr': ["10.0.0.0/24"],
                    'RoleName': [PROFILE_NAME],
                    'GroupName': [GROUP_NAME]})

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

    def test_linux_document_with_custom_vpc(self):
        custom_vpc = create_custom_vpc()
        custom_subnet = create_custom_security_group(custom_vpc["VpcId"])

        self.assertIsNotNone(custom_vpc["VpcId"])

        ssm_doc = None
        try:
            cleanup(custom_vpc["VpcId"])

            ssm_doc = ssm_testing.SSMTester(
                ssm_client=ssm_client,
                doc_filename=os.path.join(
                    DOC_DIR,
                    'Output',
                    'aws-CreateManagedLinuxInstance.json'),
                doc_name=SSM_DOC_NAME,
                doc_type='Automation'
            )

            automation_role = ssm_doc.get_automation_role(
                boto3.client('sts', region_name=REGION),
                boto3.client('iam', region_name=REGION),
                SERVICE_ROLE_NAME
            )

            ec2_client.create_key_pair(
                KeyName=KEY_PAIR_NAME
            )

            self.assertEqual(ssm_doc.create_document(), 'Active')

            execution = ssm_doc.execute_automation(
                params={
                    'AmiId': [LINUX_AMI_ID],
                    'VpcId': [custom_vpc["VpcId"]],
                    'SubnetId': [custom_subnet.id],
                    'KeyPairName': [KEY_PAIR_NAME],
                    'AutomationAssumeRole': [automation_role],
                    'InstanceType': [INSTANCE_TYPE],
                    'StackName': [CFN_STACK_NAME],
                    'RemoteAccessCidr': ["10.0.0.0/24"],
                    'RoleName': [PROFILE_NAME],
                    'GroupName': [GROUP_NAME]})

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

                    self.assertEqual(instance["VpcId"], custom_vpc["VpcId"])
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
            cleanup(custom_vpc["VpcId"])
            if ssm_doc is not None:
                ssm_doc.destroy()
