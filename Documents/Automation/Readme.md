# Automation Documents
This folder contains all the SSM Automation documents developed and published as global documents.
Any SSM document shall be named as per the following guidelines:
- The start of the document shall indicate the publisher acronym. All AWS published documents that will be developed here will begin with 'testaws-' *(as a document with aws- cannot be created outside of the team)*
- The remainder of the document name shall follow the <Verb><Noun> syntax where <Verb> indicates the action to be performed and <Noun> indicates the resource on which the action is performed. For example, a document that will start an EC2Instance will be named 'aws-StartEC2Instance' 
- All of the documents will follow the following folder structure:
    * **ProjectName** - root for every document project
        * **Design** - contains the schema in schema.json and any design notes in design.md
        * **Documents** - contains the actual Automation documents and any child Automation Documents
        * **Lambdas** - contains any lambdas that this specific document requires
        * **CloudFormationTemplates** - contains cloud formation templates that will create all the dependencies this document will require
        * **Tests** - contains all the tests required for this document 
- Tests for verifying the claims of the document will be authored as PyUnit tests

# Design Guidelines
- Wherever applicable a collection will be taken as parameter input. For instance, a “StopVM” Document will take a collection of instance Ids as a parameter rather than a single instance id. 
- If an operation can be performed on a set of resources based on tags, then the Document will support the same. For instance, a “Stop VM” Document should be able to stop a set of VMs based on specified tags. 
- Wherever possible if a set of steps within a Document forms a logical standalone operation it needs to be separated out into a separate Document. For instance, if a set of steps within a Document creates a new role, then it needs to be in a separate Document for creating a role. Use aws:executeAutomation to invoke another Document within a Document. 
- If executing a Document requires additional privileges, these will be included in a Readme.md file in the project root folder. 
- If a parameter represents a property of an AWS resource, then the parameter name should match the property name. For instance, a “Stop VM” document should contain the parameter name as InstanceIds instead of something like EC2InstanceIds (since the property name is InstanceId) 
- Documents should take AssumeRole as a parameter with the default being as available in currently published AWS Automation Documents. 
- Lambda functions invoked from a Document should be written in Python. 
- If a Document contains AssumeRole requirements for a Lambda function, this needs to be included in the Readme.md file

# Test Guidelines
- Testing framework will be PyUnit . 
	* Any Lambda functions authored should have unit test coverage of 80%. 
	* All basic operations need to be tested – create, describe, modify, delete 
	* The Test Code should create and destroy any environment required to test an Automation Document. For instance, for testing a “Stop VM” Document, the Test Code should create a VM, execute the tests and at the end destroy  the VM. This can be accomplished using a cloudformation template. The tests will create the stack based on the template and delete the stack at the end
- The Document needs to be executed using SSM Automation and the following needs to be tested: 
	* Successful invocation of automation execution 
	* Successful completion of automation execution 
	* Validating functionality of the effect that the Automation Document intends to accomplish
	* If the document can cover multiple environments then test cases should cover the test matrix. For instance, for a “Stop VM” document, test automation should cover testing stopping of Windows and Linux VMs 
	* The test should contain clear logging to debug any test failures when the test environment is no longer available. 
- The environment of the test execution – like endpoint, etc – should be configurable.This input can be from the  config file. However, the tests can assume a default


