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
"""Testing support module for SSM documents."""

from collections import OrderedDict
import json
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

    def create_stack(self, params=None, poll_interval=10):
        """Create stack and wait for its deployment to complete."""
        if params is None:
            params = []

        self.delete_stack()
        LOGGER.info('Creating stack %s' % self.stack_name)
        stack = self.cfn_client.create_stack(
            StackName=self.stack_name,
            TemplateBody=self.template_body,
            Parameters=params,
            Capabilities=['CAPABILITY_IAM']
        )
        while self.is_stack_in_status('CREATE_IN_PROGRESS') is True:
            LOGGER.info('Waiting %d seconds before checking again for successful stack creation' % poll_interval)
            time.sleep(poll_interval)
        if self.is_stack_in_status('CREATE_COMPLETE') is True:
            for i in self.cfn_client.describe_stacks(
                    StackName=self.stack_name
            )['Stacks'][0]['Outputs']:
                self.stack_outputs[i['OutputKey']] = i['OutputValue']
            return stack
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

    def delete_stack(self, poll_interval=10):
        """Delete stack if it is present."""
        if self.can_create_stack():
            # Nothing to do here
            return True
        else:
            LOGGER.info('Deleting existing stack %s' % self.stack_name)
            self.cfn_client.delete_stack(StackName=self.stack_name)
            while self.is_stack_present() is True:
                LOGGER.info('Waiting %d seconds before checking again for successful stack deletion' % poll_interval)
                time.sleep(poll_interval)
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

    def create_document(self, poll_interval=5):
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
            LOGGER.info('Waiting %d seconds before checking again for document creation' % poll_interval)
            time.sleep(poll_interval)
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
    def convert_document_to_dot_graph(doc_filename):
        """Create a graph representation of the SSM document
        in dot language to visualize when and how branching occurs."""
        # Loading the document as json
        with open(doc_filename, 'r') as jsonfile:
            json_doc = json.load(jsonfile, object_pairs_hook=OrderedDict)

        # Initializating the graph variable with the document description and the default Start and End nodes
        graph = []
        graph.append("// {}".format(json_doc["description"]))
        graph.append("digraph {")
        graph.append("    Start [label=Start]")
        graph.append("    End [label=End]")
        
        # If the document step does not explicitly define the next step on failure and on success,
        # then the next step from the document will use the following variables to create the edge
        add_edge_from_previous_step = False
        label = ""
        previous_step_name = ""

        for index, step in enumerate(json_doc["mainSteps"]):
            if add_edge_from_previous_step:
                graph.append("    {} -> {} [label={}]".format(
                    previous_step_name, step["name"], label))
                add_edge_from_previous_step = False

            # Create the edge from the Start node if this is the first node of the document
            if index == 0:
                graph.append("    {} -> {}".format("Start", step["name"]))
            # Create the two edges to the End node if this is the last node of the document, then exit the loop
            elif index == (len(json_doc["mainSteps"]) - 1):
                graph.append("    {} -> {} [label={}]".format(step["name"], "End", "onSuccess"))
                graph.append("    {} -> {} [label={}]".format(step["name"], "End", "onFailure"))
                break

            # If nextStep is used in the step, using it to create the edge,
            # else we save the current step information to be able to create the edge when inspecting the next available step
            if "nextStep" in step:
                graph.append("    {} -> {} [label={}]".format(
                    step["name"], step["nextStep"], "onSuccess"))
            # When isEnd is true, create an edge to the End node
            elif "isEnd" in step:
                if step["isEnd"] == "true":
                    graph.append("    {} -> {} [label={}]".format(step["name"], "End", "onSuccess"))
            else:
                add_edge_from_previous_step = True
                label = "onSuccess"
                previous_step_name = step["name"]

            # If onFailure is Abort or not specified, create an edge to the End node.
            if "onFailure" in step:
                if step["onFailure"] == "Abort":
                    graph.append("    {} -> {} [label={} color=\"red\"]".format(
                        step["name"], "End", "onFailure"))
                # If onFailure is Continue, we look for nextStep,
                # or save the current step information to be able to create the edge when inspecting the next available step
                elif step["onFailure"] == "Continue":
                    if "nextStep" in step:
                        label="onFailure color=\"red\""
                        if "isCritical" in step:
                            if step["isCritical"] == "false":
                                label="onFailure"
                        graph.append("    {} -> {} [label={}]".format(
                            step["name"], step["nextStep"], label))
                    else:
                        add_edge_from_previous_step = True
                        label="onFailure color=\"red\""
                        previous_step_name = step["name"]
                # Lastly, retrieve the next step from onFailure directly
                else:
                    label="onFailure color=\"red\""
                    if "isCritical" in step:
                        if step["isCritical"] == "false":
                            label="onFailure"
                    graph.append("    {} -> {} [label={}]".format(
                        step["name"], step["onFailure"].replace("step:", ""), label))
            else:
                graph.append("    {} -> {} [label={}]".format(
                        step["name"], "End", "onFailure color=\"red\""))

        graph.append("}")

        return "\n".join(graph)

    @staticmethod
    def automation_execution_status(ssm_client, execution_id,
                                    block_on_waiting=True, status_callback=None, poll_interval=10):
        """Return execution status, waiting for completion if in progress."""

        statuses = PENDING_AUTOMATION_STATUS_WITH_WAITING
        if not block_on_waiting:
            statuses = PENDING_AUTOMATION_STATUS

        while True:
            current_status = ssm_client.get_automation_execution(
                AutomationExecutionId=execution_id)['AutomationExecution']['AutomationExecutionStatus']

            if status_callback is not None:
                status_callback({"status": current_status})

            if current_status not in statuses:
                return current_status

            LOGGER.info('Waiting %d seconds before checking again for automation conclusion' % poll_interval)
            time.sleep(poll_interval)

    @staticmethod
    def ensure_no_instance_in_state(ec2_client, state, instances=None, poll_interval=10):
        """Wait for a list of instances to stop being in a specified state."""
        if instances is None:
            instances = []

        while any(d['InstanceState']['Name'] == state for d in ec2_client.describe_instance_status(  # noqa pylint: disable=line-too-long
                InstanceIds=instances,
                IncludeAllInstances=True
        )['InstanceStatuses']):
            LOGGER.info('Instance(s) still found in state %s; waiting %d seconds before checking state again' %
                        state, poll_interval)
            time.sleep(poll_interval)

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


class VPCTester(object):
    def __init__(self, ec2):
        self.ec2 = ec2

    def find_default_subnets(self):
        ec2 = self.ec2

        default_vpc_filters = [{
            'Name': 'isDefault',
            'Values': ['true']
        }]

        available_subnets = []

        for vpc in list(ec2.vpcs.filter(Filters=default_vpc_filters)):
            for subnet in list(vpc.subnets.all()):
                available_subnets.append(subnet) if subnet.state == 'available' else False

        return available_subnets
