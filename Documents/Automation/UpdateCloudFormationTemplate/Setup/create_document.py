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
        return json.load(fp)


def process():
    # replace all cloud formation template lambda section with actual code.
    template = open_cloud_formation_template("UpdateCFTemplate.yml")
    insert_lambda_in_cft(template, "UpdateCFLambda", "update_cf_template.py")

    # replace document create stack with actual template body.
    document = open_document("aws-UpdateCloudFormationTemplate.json")
    insert_cft_in_document(document, "createDocumentStack", yaml.safe_dump(template, indent=2))
    print json.dumps(document, indent=2)


if __name__ == '__main__':
    process()

