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
SERVICE_ROLE_NAME = CONFIG.get('general', 'automation_service_role_name')

AMI_ID = CONFIG.get('windows', 'windows2016.{}'.format(REGION))
INSTANCE_TYPE = CONFIG.get('windows', 'instance_type')

SSM_DOC_NAME = PREFIX + 'automation-asg'
CFN_STACK_NAME = PREFIX + 'automation-asg'

logging.basicConfig(level=CONFIG.get('general', 'log_level').upper())
LOGGER = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(level=logging.WARNING)

vpcUtil = ssm_testing.VPCTester(boto3.resource('ec2', region_name=REGION))

ec2_client = boto3.client('ec2', region_name=REGION)
as_client = boto3.client('autoscaling', region_name=REGION)


class TestCase(unittest.TestCase):
    @staticmethod
    def test_document():
        cfn_client = boto3.client('cloudformation', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        available_subnets = vpcUtil.find_default_subnets()

        # ensure the account being used has a default VPC.
        assert len(available_subnets) > 0, "No default subnet available for testing"

        ssm_doc = ssm_testing.SSMTester(
            ssm_client=ssm_client,
            doc_filename=os.path.join(
                DOC_DIR,
                'Documents/aws-PatchWindowsInASG.json'),
            doc_name=SSM_DOC_NAME,
            doc_type='Automation'
        )

        test_cf_stack = ssm_testing.CFNTester(
            cfn_client=cfn_client,
            template_filename=os.path.abspath(os.path.join(
                DOC_DIR,
                'Tests/CloudFormationTemplates/ASG.yml')),
            stack_name=CFN_STACK_NAME
        )

        automation_role = ssm_doc.get_automation_role(
            boto3.client('sts', region_name=REGION),
            boto3.client('iam', region_name=REGION),
            SERVICE_ROLE_NAME
        )

        LOGGER.info('Creating AutoScaling Group for testing')
        stack_param = {
            'AMI': AMI_ID,
            'Subnets': available_subnets[0].id,
            'InstanceType': INSTANCE_TYPE
        }
        test_cf_stack.create_stack([
            {'ParameterKey': key, 'ParameterValue': value} for key, value in stack_param.iteritems()])

        try:
            asg_name = test_cf_stack.stack_outputs["ASGName"]

            LOGGER.info("Creating automation document")
            assert ssm_doc.create_document() == 'Active', 'Document not created successfully'

            LOGGER.info("Waiting for an instance to become ready...")
            working_instance = asg_wait_for_running_instance(asg_name, 1)[0]

            LOGGER.info("Checking for AutoPatchInstanceInASG tag on instance.")
            check_tag_exist(working_instance, 'AutoPatchInstanceInASG', False)

            LOGGER.info("Executing SSM automation document to update instance on {}".format(working_instance))
            execution = ssm_doc.execute_automation(
                params={'InstanceId': [working_instance],
                        'AutomationAssumeRole': [automation_role]})

            # Collect tag change and asg instance lifecycle change.
            tag_changes = [None]
            asg_status_changes = []
            asg_status_ignores = ["EnteringStandby", "Pending"]

            # Status callback to collect any necessary data
            def status_callback(_):
                collect_tag_change(working_instance, "AutoPatchInstanceInASG", tag_changes),
                collect_asg_status_change(asg_name, working_instance, asg_status_ignores, asg_status_changes)

            # Wait for SSM to finish while collecting value change (callback).
            result = ssm_doc.automation_execution_status(ssm_client, execution, status_callback=status_callback)

            # Verify tag change.
            LOGGER.info(tag_changes)
            expected_tag_change = [
                None,
                "InProgress",
                "Completed"
            ]
            assert tag_changes == expected_tag_change, 'Tag did not follow sequence.'

            # Verify instance status change.
            LOGGER.info(asg_status_changes)
            expected_status_change_sequence = [
                "InService",
                "Standby",
                "InService"
            ]
            is_status_change_expected = asg_status_changes == expected_status_change_sequence
            assert is_status_change_expected, 'ASG instant lifecycle did not match expected.'

            LOGGER.info('Verifying automation executions have concluded successfully')
            assert result == 'Success', 'Document did not complete'

        finally:
            test_cf_stack.delete_stack()
            ssm_doc.destroy()


def asg_wait_for_running_instance(asg_name, number_of_instance, max_wait_sec=60):
    """
    Wait for ASG to start up some instance and return the instance id.

    :param asg_name: AutoScaling group's name.
    :param number_of_instance: Max number of instance to return.
    :param max_wait_sec: Number of sec, this function should wait for an instance.
    :return: list of instance id
    """
    found_instances = []
    sleep_counter = 0

    while True:
        asg_lists = as_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        assert len(asg_lists["AutoScalingGroups"]) > 0, "No AutoScaling Group found"

        instances = asg_lists["AutoScalingGroups"][0]["Instances"]
        if len(instances) > 0:
            describe_res = ec2_client.describe_instance_status(
                InstanceIds=[x["InstanceId"] for x in instances],
                IncludeAllInstances=True
            )

            for d in describe_res['InstanceStatuses']:
                instance_id = d["InstanceId"]
                if d['InstanceState']['Name'] == 'running' and instance_id not in found_instances:
                    found_instances.append(d["InstanceId"])

                    if len(found_instances) == number_of_instance:
                        return found_instances

        assert sleep_counter * 10 < max_wait_sec, "Unable to find running instance"

        sleep_counter += 1
        time.sleep(10)


def collect_asg_status_change(name, instance_id, ignores, test_result):
    """
    Monitor Auto Scaling Group Instance lifecycle status and append changes to test_result.

    :param name: Auto Scaling Group name to monitor.
    :param instance_id:  Instance id to monitor.
    :param ignores: List of state to ignore.
    :param test_result: Location to append result.
    """
    describe_res = as_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[name]
    )["AutoScalingGroups"][0]

    for instance in describe_res["Instances"]:
        if instance["InstanceId"] == instance_id:
            state = instance["LifecycleState"]
            if state in ignores:
                continue

            if len(test_result) > 0:
                if test_result[-1] != state:
                    LOGGER.info("ASG Change Detection: {}".format(state))
                    test_result.append(state)
            else:
                LOGGER.info("ASG Change Detection: {}".format(state))
                test_result.append(state)


def collect_tag_change(instance_id, tag_name, test_result):
    """
    Collect tag change for a given instance and record in test_result and append changes to test_result.

    :param instance_id: Instance id to check and get result.
    :param tag_name: Tag to monitor.
    :param test_result: Location to append result.
    """
    describe_res = ec2_client.describe_instances(
        InstanceIds=[
            instance_id
        ]
    )
    instance = describe_res["Reservations"][0]["Instances"][0]

    value = None
    for tag in instance["Tags"]:
        if tag["Key"] == tag_name:
            value = tag["Value"]
            break

    if len(test_result) > 0:
        if test_result[-1] != value:
            LOGGER.info("Tag Change Detection: {}".format(value))
            test_result.append(value)
    else:
        LOGGER.info("Tag Change Detection: {}".format(value))
        test_result.append(value)


def check_tag_exist(instance_id, tag_name, is_present, is_value=None):
    """
    Check if a tag exist for a given instance id

    :param instance_id: instance id to check
    :param tag_name: tag name to check
    :param is_present: specify if tag should be present
    :param is_value: if present, check if the value matches
    """
    describe_res = ec2_client.describe_instances(
        InstanceIds=[
            instance_id
        ]
    )
    instance = describe_res["Reservations"][0]["Instances"][0]

    is_found = False
    value = None
    for tag in instance["Tags"]:

        if tag["Key"] == tag_name:
            is_found = True
            value = tag["Value"]
            break

    assert is_found == is_present, "{} name status: {} expected {}".format(tag_name, is_found, is_present)
    if is_found:
        assert value == is_value, "{} does not match expected {}".format(value, is_value)


if __name__ == '__main__':
    unittest.main()

