# Design Notes

**Automation Documents**

There are 4 automation documents in this sub project. They are:
* aws-CreateManagedInstanceWindows.json - automation document for creating a Windows managed instance
* aws-CreateManagedInstanceLinux.json - automation document for creating a Linux managed instance
* aws-CreateManagedInstanceProfile.json - automation document that will create the role required for creating a managed instance
* aws-CreateSecurityGroup.json - automation document to create the security group required for remote connectivity on the desired platforms

**Document Structure**

Given that the documents attempt to perform tasks that do not have appropriate Automation actions, the document does the following:
* Create a lambda function, using a cloud formation stack invoked by CreateStack action. This lambda function will perform the necessary steps using boto3
* Invoke the lambda function using InvokeLambda action
* Delete the lambda function using the DeleteStack action

**Makefile**

There is a makefile to generate the required automation documents. This is because the automation document contains the cloudformation template inline as a JSON escaped string. The cloud formation template inturn contains the lambda code inline as a JSON escaped string. This model ensures that the document is self-contained and has no external dependencies. The makefile downloads ```escapejson``` python module and creates the necessary escaped automation document.

To clear the output folder use
```
make clean
```

To generate the documents use

```
make
```