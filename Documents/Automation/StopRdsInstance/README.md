# Stop RDS Instance

Stops a DB instance. When you stop a DB instance, Amazon RDS retains the DB instance's metadata, including its endpoint,
DB parameter group, and option group membership. Amazon RDS also retains the transaction logs so you can do a 
point-in-time restore if necessary. 

## Inputs

#### InstanceId
  * The RDS instance to stop.
  * Type: String
  * Required: True

## Outputs
The automation execution has no outputs.
