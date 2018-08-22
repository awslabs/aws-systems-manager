# Start RDS instance based on InstanceId

## Document Design

### Inputs
* (Required) Database Instance Identifier.
* (Optional) The ARN of the role assumed by lambda.
* (Optional) The ARN of the role that allows Automation to perform the actions on your behalf.

### Steps
1. Create Stack (aws:createStack)
	* Input
		* LambdaAssumeRole - role lambda will be executed as.
	* Resources
		* Create RDS create-instance Lambda
		* Create RDS stop-instance Lambda
		* Create lambda role if LambdaAssumeRole is not provided.
2. Invoke RDS start Lambda (aws:invokeLambdaFunction)
	* Input
		* DB Instance Identifier
	* Steps
		* Start RDS instance.
3. Invoke RDS start Lambda (aws:invokeLambdaFunction)
    * Input
        * DB Instance Identifier
        * Accepted RDS state
    * Steps
        * Poll RDS instance information for state
4. Delete Stack (aws:deleteStack)


### Test

#### Document Test
1. Create resources using CFT
	* Create Automation Assume Role
	* Create RDS Instance
	* Stop RDS Instance
2. Execute Document
3. Verify RDS instance started correctly
4. Tear down template
