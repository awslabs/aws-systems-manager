# Stop RDS instance based on id

## Notes

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
      * Create RDS start Lambda
      * Create lambda role if LambdaAssumeRole is not provided.
2. Invoke RDS start Lambda (aws:invokeLambdaFunction)
   * Input
      * DB Instance Identifier
   * Steps
      * Stop RDS instance.
3. Invoke RDS wait lambda (aws:invokeLambdaFunction)
   * Input
      * DB Instance Identifier
      * Accepted RDS state
3. Delete Stack (aws:deleteStack)

### Test

#### Document Test

1. Create resources using CFT
   * Create Automation Assume Role
   * Create RDS Instance
2. Execute Document
3. Verify RDS instance stopped correctly
4. Tear down template