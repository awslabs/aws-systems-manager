# Reboot RDS Instance

## Document Design

Refer to schema.json

### Steps
1. Create Stack (aws:createStack)
	* Input
		* LambdaAssumeRole - role lambda will be executed as.
	* Resources
		* Create RDS *reboot* Lambda
		* Create RDS *wait_for_state* Lambda
		* Create lambda role if LambdaAssumeRole is not provided.
2. Invoke *reboot* Lambda (aws:invokeLambdaFunction)
	* Input
		* RDS Instance Identifier
	* Steps
		* Reboot RDS instance.
3. Invoke *wait_for_state* Lambda (aws:invokeLambdaFunction)
    * Input
        * DB Instance Identifier
        * Accepted RDS state
    * Steps
        * Poll RDS instance information for state
4. Delete Stack (aws:deleteStack)

  
## Tests

#### Document Test
1. Create resources using CFT
	* Create Automation Assume Role
	* Create RDS Instance
2. Execute Document
3. Verify RDS instance rebooted correctly
4. Tear down template

### Building Document

```
make
```

1. Parse CloudFormation Template
2. Embed lambda functions located in Documents/Lambdas/ into CloudFormation Template 
	A. reboot.py
	B. wait_for_state.py
3. Parse Documents/aws-RebootRds.json
4. Embed CloudFormation Template into Automation Document.
5. Output new Document into ./Output

### Cleaning Document

```
make clean
```

1. Delete content of ./Output folder

### Test

```
make test
```

1. Discover all test in this folder.
2. Execute all tests
