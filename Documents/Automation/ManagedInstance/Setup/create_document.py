import os
import sys

from collections import OrderedDict
import json
import yaml

LAMBDA_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "../Documents/Lambdas"
))
CFT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "../Documents/CloudFormationTemplates"
))
DOCUMENT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "../Documents"
))


def aws_tag_multi_constructor(loader, tag_suffix, node):
    if tag_suffix not in ['Ref', 'Condition']:
        tag_suffix = "Fn::{}".format(tag_suffix)

    if tag_suffix == "Fn::GetAtt":
        result = node.value.split(".")
    elif isinstance(node, yaml.ScalarNode):
        result = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        result = loader.construct_sequence(node)
    elif isinstance(node, yaml.MappingNode):
        result = loader.construct_mapping(node)
    else:
        raise "Bad value for {}".format(tag_suffix)

    return {tag_suffix: result}


yaml.add_multi_constructor("!", aws_tag_multi_constructor)


def insert_lambda_in_cft(template, resource_name, lambda_file):
    lambda_file = os.path.normpath(os.path.join(LAMBDA_DIR, lambda_file))

    with open(lambda_file) as fp:
        # to shave some bytes we convert 4 spaces to tab
        file_content = fp.read().replace("    ", "\t")

        file_size = len(file_content)
        print >> sys.stderr, lambda_file + " is " + str(file_size) + "/4096 of max size"
        assert file_size <= 4096, "Lambda function must be less then 4096"
        template["Resources"][resource_name]["Properties"]["Code"]["ZipFile"] = file_content


def insert_cft_in_document(template, step_name, cft_template):
    print >> sys.stderr, "Cloud Formation Template is " + str(len(cft_template)) + "/51200 of max size"
    assert len(cft_template) < 51200, "CloudFormation template too long, must be less then 50000"
    for step in template["mainSteps"]:
        if step["name"] == step_name:
            step["inputs"]["TemplateBody"] = cft_template
            break


def open_cloud_formation_template(file_name):
    cloud_formation_file = os.path.normpath(os.path.join(CFT_DIR, file_name))
    with open(cloud_formation_file) as fp:
        file_content = fp.read()

        return yaml.load(file_content)


def open_document(file_name):
    cloud_formation_file = os.path.normpath(os.path.join(DOCUMENT_DIR, file_name))
    with open(cloud_formation_file) as fp:
        # to preserve the parameter order we need to load it in an ordered list.
        return json.load(fp, object_pairs_hook=OrderedDict)


def replace_param_default(template, name, default):
    for key, value in template["parameters"].iteritems():
        if key == name:
            template["parameters"][key]["default"] = default
            break


def update_document(main_document, subset_document):
    processed = set([])
    for item, value in main_document.iteritems():
        if item in subset_document:
            if isinstance(subset_document[item], dict):
                update_document(value, subset_document[item])
                processed.add(item)
        else:
            main_document[item] = value

    for item, value in subset_document.iteritems():
        if item not in processed:
            main_document[item] = value


def insert_approval_step(document, message, before=None):
    index = 0
    if before is not None:
        for step in document["mainSteps"]:
            if step == before:
                break
            index += 1

    document["mainSteps"].insert(0, {
        "name": "approve",
        "action": "aws:approve",
        "onFailure": "Abort",
        "inputs": {
            "NotificationArn": "{{SNSTopicArn}}",
            "Message": message,
            "MinRequiredApprovals": 1,
            "Approvers": "{{Approvers}}"
        }
    })


def sort_param(document, sort_list):
    document["parameters"] = OrderedDict(
        sorted(
            document["parameters"].items(),
            key=lambda t: sort_list.index(t[0])
        ))


def process(platform, type):
    assert platform in ("windows", "linux"), "Unsupported platform"

    # replace all cloud formation template lambda section with actual code.
    template = open_cloud_formation_template("CreateManagedInstance.yml")
    insert_lambda_in_cft(template, "CollectInformationLambda", "collect_info.py")
    insert_lambda_in_cft(template, "CollectSubnetInfoLambda", "subnet_info.py")
    insert_lambda_in_cft(template, "InstanceProfileLambda", "create_instance_profile.py")
    insert_lambda_in_cft(template, "SecurityGroupLambda", "create_security_group.py")

    # replace document create stack with actual template body.
    document = open_document("aws-CreateManagedInstance.json")
    insert_cft_in_document(document, "createManagedInstanceStack", yaml.safe_dump(template, indent=2))

    merge_document = None
    if platform == "windows":
        merge_document = open_document("aws-CreateManagedWindowsInstance.json")
    elif platform == "linux":
        merge_document = open_document("aws-CreateManagedLinuxInstance.json")

    if merge_document is not None:
        update_document(document, merge_document)

    if type == "approve":
        document["description"] = document["description"] + " with approval"
        update_document(document, open_document("aws-CreateManagedInstanceWithApproval.json"))
        insert_approval_step(document, "Approval required to create a managed instance", before="createManagedInstanceStack")

    sort_param(document, [
        "AmiId",
        "VpcId",
        "RoleName",
        "GroupName",
        "InstanceType",
        "KeyPairName",
        "RemoteAccessCidr",
        "Approvers",
        "SNSTopicArn",
        "StackName",
        "AutomationAssumeRole",
        "SubnetId"])

    print json.dumps(document, indent=2)


if __name__ == '__main__':
    process(sys.argv[1], sys.argv[2])
