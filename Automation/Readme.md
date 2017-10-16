# Automation Documents
This folder contains all the SSM Automation documents developed and published as global documents.
Any SSM document shall be named as per the following guidelines:
- The start of the document shall indicate the publisher acronym. All AWS published documents will begin with 'aws-'
- The remainder of the document name shall follow the <Verb><Noun> syntax where <Verb> indicates the action to be performed and <Noun> indicates the resource on which the action is performed. For example, a document that will start an EC2Instance will be named 'aws-StartEC2Instance' 
- All of the documents will follow the following folder structure:
    * **ProjectName** - root for every document project
    * **Design** - contains the schema in schema.json and any design notes in design.md
    * **Documents** - contains the actual Automation documents and any child Automation Documents
    * **Lambdas** - contains any lambdas that this specific document requires
    * **CloudFormationTemplates** - contains cloud formation templates that will create all the dependencies this document will require
    * **Tests** - contains all the tests required for this document 
- Tests for verifying the claims of the document will be authored as PyUnit tests

