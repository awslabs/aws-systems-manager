#!/usr/bin/env python
"""Testing support module for SSM documents."""

import logging
import time

LOGGER = logging.getLogger(__name__)
PENDING_AUTOMATION_STATUS = ('Pending', 'InProgress')
PENDING_AUTOMATION_STATUS_WITH_WAITING = ('Pending', 'InProgress', 'Waiting')
PENDING_DOC_STATUS = ('Creating', 'Updating')


class CFNTester(object):
    """CloudFormation stack test class."""

    def __init__(self, cfn_client, template_filename, stack_name):
        """Create object variables."""
        self.cfn_client = cfn_client
        with open(template_filename, 'r') as jsonfile:
            self.template_body = jsonfile.read()
        self.stack_name = stack_name
        self.stack_outputs = {}

    def create_stack(self, params=None):
        """Create stack and wait for its deployment to complete."""
        if params is None:
            params = []

        self.delete_stack()
        LOGGER.info('Creating stack %s', self.stack_name)
        self.cfn_client.create_stack(
            StackName=self.stack_name,
            TemplateBody=self.template_body,
            Parameters=params,
            Capabilities=['CAPABILITY_IAM']
        )
        while self.is_stack_in_status('CREATE_IN_PROGRESS') is True:
            LOGGER.info('Waiting 10 seconds before checking again for '
                        'successful stack creation')
            time.sleep(10)
        if self.is_stack_in_status('CREATE_COMPLETE') is True:
            for i in self.cfn_client.describe_stacks(
                    StackName=self.stack_name
            )['Stacks'][0]['Outputs']:
                self.stack_outputs[i['OutputKey']] = i['OutputValue']
            return True
        else:
            raise ValueError('CFN stack did not create successfully')

    def is_stack_in_status(self, status):
        """Determine if the stack is currently in a matching status."""
        response = self.cfn_client.describe_stacks(StackName=self.stack_name)
        return response['Stacks'][0]['StackStatus'] == status

    def is_stack_present(self):
        """Determine if the stack exists."""
        stacks = []
        paginator = self.cfn_client.get_paginator('list_stacks')
        page_iterator = paginator.paginate()
        for page in page_iterator:
            stacks.extend(page['StackSummaries'])
        return any(i['StackName'] == self.stack_name and i['StackStatus'] != 'DELETE_COMPLETE' for i in stacks)  # noqa pylint: disable=line-too-long

    def can_create_stack(self):
        if self.is_stack_present():
            return self.is_stack_in_status('DELETE_COMPLETE')
        else:
            return True

    def delete_stack(self):
        """Delete stack if it is present."""
        if self.can_create_stack():
            # Nothing to do here
            return True
        else:
            LOGGER.info('Deleting existing stack %s', self.stack_name)
            self.cfn_client.delete_stack(StackName=self.stack_name)
            while self.is_stack_present() is True:
                LOGGER.info('Waiting 10 seconds before checking again for '
                            'successful stack deletion')
                time.sleep(10)
            return True


class SSMTester(object):
    """SSM document test class."""

    def __init__(self, ssm_client, doc_filename, doc_name, doc_type):
        """Create object variables."""
        self.ssm_client = ssm_client
        with open(doc_filename, 'r') as jsonfile:
            self.doc_content = jsonfile.read()
        self.doc_name = doc_name
        self.doc_type = doc_type

    def create_document(self):
        """Upload document and wait for its deployment to complete."""
        if self.document_exists() is True:
            LOGGER.info('Deleting previously deployed document')
            self.destroy()
        self.ssm_client.create_document(
            Content=self.doc_content,
            Name=self.doc_name,
            DocumentType=self.doc_type
        )
        LOGGER.info('Verifying SSM document creation is complete')
        while self.ssm_client.describe_document(
                Name=self.doc_name
        )['Document']['Status'] in PENDING_DOC_STATUS:
            LOGGER.info('Waiting 5 seconds before checking again for '
                        'document creation')
            time.sleep(5)
        return self.ssm_client.describe_document(
            Name=self.doc_name
        )['Document']['Status']

    def document_exists(self):
        """Return true if document has been deployed previously."""
        return len(self.ssm_client.list_documents(
            DocumentFilterList=[{'key': 'Name', 'value': self.doc_name}]
        )['DocumentIdentifiers']) == 1

    def execute_automation(self, params=None):
        """Execute SSM document."""
        if params is None:
            params = {}
        return self.ssm_client.start_automation_execution(
            DocumentName=self.doc_name,
            Parameters=params
        )['AutomationExecutionId']

    def destroy(self):
        """Delete SSM document."""
        self.ssm_client.delete_document(Name=self.doc_name)

    @staticmethod
    def automation_execution_status(ssm_client, execution_id, block_on_waiting=True):
        """Return execution status, waiting for completion if in progress."""
        statuses = PENDING_AUTOMATION_STATUS_WITH_WAITING
        if not block_on_waiting:
            statuses = PENDING_AUTOMATION_STATUS
        while ssm_client.get_automation_execution(
                AutomationExecutionId=execution_id
        )['AutomationExecution']['AutomationExecutionStatus'] in statuses:  # noqa pylint: disable=line-too-long
            LOGGER.info('Waiting 10 seconds before checking again '
                        'for automation conclusion')
            time.sleep(10)
        return ssm_client.get_automation_execution(
            AutomationExecutionId=execution_id
        )['AutomationExecution']['AutomationExecutionStatus']

    @staticmethod
    def ensure_no_instance_in_state(ec2_client, state, instances=None):
        """Wait for a list of instances to stop being in a specified state."""
        if instances is None:
            instances = []

        while any(d['InstanceState']['Name'] == state for d in ec2_client.describe_instance_status(  # noqa pylint: disable=line-too-long
                InstanceIds=instances,
                IncludeAllInstances=True
        )['InstanceStatuses']):
            LOGGER.info('Instance(s) still found in state %s; waiting 10 '
                        'seconds before checking state again', state)
            time.sleep(10)

    @staticmethod
    def role_exists(iam_client, role_name):
        """Return true if IAM role exists."""
        roles = []
        paginator = iam_client.get_paginator('list_roles')
        page_iterator = paginator.paginate()
        for page in page_iterator:
            roles.extend(page['Roles'])
        return any(i['RoleName'] == role_name for i in roles)

    @staticmethod
    def get_automation_role(sts_client, iam_client, role_name):
        """Determine automation role ARN."""
        account_num = sts_client.get_caller_identity()['Account']
        if SSMTester.role_exists(iam_client, role_name):
            return "arn:aws:iam::%s:role/%s" % (account_num, role_name)
        else:
            raise ValueError('Automation role %s does not exist' % role_name)
