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
import boto3


def handler(event, context):
    instance_id = event["InstanceId"]
    new_instance_type = event["InstanceType"]

    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instance_id)

    # Migrated to a step
    # state_code = instance.state['Code']
    # if state_code == 16 or state_code == 64:
    #     instance.stop()
    #     print "Stopping"
    #     instance.wait_until_stopped()
    #     print "Stopped"

    print "Modifying instance type"
    instance.modify_attribute(InstanceType={
        'Value': new_instance_type
    })

    # Migrated to a step
    # instance.start()
    # print "Starting"
    # instance.wait_until_running()
    # print "Now running"

