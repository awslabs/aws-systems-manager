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
