#!/usr/bin/env python
"""Main test file for SSM document."""

import glob
import os
import time
import unittest

import boto3
import demjson

REGION = 'us-east-1'
AMIID = 'ami-cd0f5cb6'  # any valid AMI in the region will work
SSMDOCNAME = 'test-automation_startinstance'
PENDING_AUTOMATION_STATUS = ('Pending', 'InProgress', 'Waiting')
PENDING_DOC_STATUS = ('Creating', 'Updating')

DOCSDIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    'Documents'
)


class TestCase(unittest.TestCase):
    """Main test class for SSM document."""

    @staticmethod
    def test_jsonlinting():
        """Verify correct json syntax."""
        for i in glob.glob(os.path.join(DOCSDIR, '*.json')):
            assert demjson.jsonlint('jsonlint').main([i]) == 0, (
                'JSON documents are not well formed')

    @staticmethod
    def testdocument():
        """Verify correct deployment and use of document."""
        ec2_client = boto3.client('ec2', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        print 'Starting 3 instances for testing'
        run_response = ec2_client.run_instances(
            ImageId=AMIID,
            InstanceType='t2.micro',
            MaxCount=3,
            MinCount=3
        )
        try:
            print 'Ensuring instances have started'
            while any(d['InstanceState']['Name'] == 'pending' for d in ec2_client.describe_instance_status(
                    InstanceIds=[
                        x['InstanceId'] for x in run_response['Instances']
                    ],
                    IncludeAllInstances=True
            )['InstanceStatuses']):
                print ('Waiting 15 seconds before checking again for instance '
                       'startup')
                time.sleep(15)

            # Stop instances
            print 'Stopping instances'
            ec2_client.stop_instances(
                InstanceIds=[
                    x['InstanceId'] for x in run_response['Instances']
                ]
            )

            # Create automation document
            print 'Creating automation document'
            with open(os.path.join(DOCSDIR, 'aws-StartEC2Instance.json'),
                      'r') as jsonfile:
                doc_contents = jsonfile.read()
            ssm_client.create_document(
                Content=doc_contents,
                Name=SSMDOCNAME,
                DocumentType='Automation'
            )
            print 'Verifying SSM document creation is complete'
            while ssm_client.describe_document(
                    Name=SSMDOCNAME
            )['Document']['Status'] in PENDING_DOC_STATUS:
                print ('Waiting 5 seconds before checking again for document '
                       'creation')
                time.sleep(5)
            assert ssm_client.describe_document(
                Name=SSMDOCNAME
            )['Document']['Status'] == 'Active', ('Document not created '
                                                  'successfully')

            print 'Ensuring instances have stopped'
            while any(d['InstanceState']['Name'] == 'stopping' for d in ec2_client.describe_instance_status(
                    InstanceIds=[
                        x['InstanceId'] for x in run_response['Instances']
                    ],
                    IncludeAllInstances=True
            )['InstanceStatuses']):
                print ('Waiting 15 seconds before checking again for instance '
                       'stopping')
                time.sleep(15)

            # Start of single instance
            print 'Running automation to start single instance'
            instance_0 = run_response['Instances'][0]['InstanceId']
            run_doc_res_0 = ssm_client.start_automation_execution(
                DocumentName=SSMDOCNAME,
                Parameters={'InstanceIds': [instance_0]}
            )

            # Start of multiple instances
            print 'Running automation to start multiple instances'
            instances_1_2 = [run_response['Instances'][1]['InstanceId'],
                             run_response['Instances'][2]['InstanceId']]
            run_doc_res_1 = ssm_client.start_automation_execution(
                DocumentName=SSMDOCNAME,
                Parameters={'InstanceIds': instances_1_2}
            )

            # Verify instance startup
            for i in [run_doc_res_0['AutomationExecutionId'],
                      run_doc_res_1['AutomationExecutionId']]:
                print 'Verifying automation executions have concluded'
                while ssm_client.get_automation_execution(
                        AutomationExecutionId=i
                )['AutomationExecution']['AutomationExecutionStatus'] in PENDING_AUTOMATION_STATUS:
                    print ('Waiting 10 seconds before checking again for '
                           'automation conclusion')
                    time.sleep(10)
                assert ssm_client.get_automation_execution(
                    AutomationExecutionId=i
                )['AutomationExecution']['AutomationExecutionStatus'] == 'Success', 'Instance not started'

            describe_res = ec2_client.describe_instance_status(
                InstanceIds=[
                    x['InstanceId'] for x in run_response['Instances']
                ],
                IncludeAllInstances=True
            )
            assert all(d['InstanceState']['Name'] == 'running' for d in describe_res['InstanceStatuses']) is True, (
                'Instances not started')

        finally:
            if len(run_response['Instances']):
                ec2_client.terminate_instances(
                    InstanceIds=[
                        x['InstanceId'] for x in run_response['Instances']
                        if x['State']['Name'] != 'terminated'
                    ]
                )
            ssm_client.delete_document(Name=SSMDOCNAME)


if __name__ == '__main__':
    unittest.main()
