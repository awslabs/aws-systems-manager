#!/usr/bin/env python
"Escape JSON"
import json
import sys

from escapejson import escapejson

def escape_json(strcontents):
    "JSON escape the given string"
    jsondumps = json.dumps(strcontents)
    return escapejson(jsondumps)

def escape_file(filename):
    "JSON escape the given file"
    with open(filename, 'r') as inputfile:
        return escape_json(inputfile.read())

def create_cloud_formation_template(cfname, lambdafilename):
    "Create a cloud formation template with the given lambda"
    lambdacontents = escape_file(lambdafilename)

    with open(cfname, 'r') as cffile:
        cfcontents = cffile.read()
        print "Creating cloudformation template from file " + cfname + " and inserting lambda contents from " + lambdafilename
        cfcontents = cfcontents.replace("\"{0}\"", lambdacontents)
        return cfcontents

def create_automation_document(docname, inputdocname, cfname, lambdafilename):
    "Create an SSM Automation document"
    cfcontents = create_cloud_formation_template(cfname, lambdafilename)

    doccontents = ""
    with open(inputdocname, 'r') as docfile:
        doccontents = docfile.read()
        print "Creating SSM automation document from " + inputdocname + " and replacing cloudformation template contents inline"
        doccontents = doccontents.replace("\"{0}\"", escape_json(cfcontents))

    with open(docname, 'w') as docfile:
        docfile.write(doccontents)

def create_ssm_automation_documents():
    "Create the automation documents based on substitution"
    create_automation_document("./Output/awstest-CreateSecurityGroup.json", "./Documents/awstest-CreateSecurityGroup.json", "./CloudFormationTemplates/CloudFormationLambdaSecurityGroup.json", "./Lambdas/lambda_invoker_sg.py")
    create_automation_document("./Output/awstest-CreateManagedInstanceProfile.json", "./Documents/awstest-CreateManagedInstanceProfile.json", "./CloudFormationTemplates/CloudFormationLambdaManagedInstanceProfile.json", "./Lambdas/lambda_invoker_mip.py")

create_ssm_automation_documents()