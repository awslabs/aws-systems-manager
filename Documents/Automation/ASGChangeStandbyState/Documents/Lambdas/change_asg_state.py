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
import logging

import boto3


def handler(event, context):
    """
    Changes the state of an instance in an autoscaling group. The IAM role running this lambda requires the following
    permissions:
    {
      "Effect": "Allow",
      "Action": [
        "autoscaling:EnterStandby",
        "autoscaling:ExitStandby",
        "autoscaling:DescribeAutoScalingInstances
      ],
      "Resource": "*"
    }
    :param event: Defined fields:
        {
          "State": "EnterStandby|ExitStandby",
          "InstanceId": "i-1234567890",
          "ASGName": "MyASGName",
          "ShouldDecrement": true|false
        }
    The ShouldDecrement field is only used for EnterStandby and ignored otherwise
    """
    as_client = boto3.client('autoscaling')
    # The state to transition to. Options are EnterStandby and ExitStandby
    state = event.get('State')
    instance_id = event.get('InstanceId')
    decrement = event.get('ShouldDecrement', False)

    assert state in {'EnterStandby', 'ExitStandby'}, 'Invalid state provided'
    assert instance_id is not None, 'InstanceId must be specified'

    instances = as_client.describe_auto_scaling_instances(InstanceIds=[instance_id])
    if len(instances.get("AutoScalingInstances", [])) > 0:
        asg_name = instances["AutoScalingInstances"][0]["AutoScalingGroupName"]
        if state == 'EnterStandby':
            print "Enter Standby: {} {}".format(instance_id, asg_name)
            as_client.enter_standby(InstanceIds=[instance_id],
                                    AutoScalingGroupName=asg_name,
                                    ShouldDecrementDesiredCapacity=decrement)
        else:
            print "Exit Standby: {} {}".format(instance_id, asg_name)
            as_client.exit_standby(InstanceIds=[instance_id], AutoScalingGroupName=asg_name)


