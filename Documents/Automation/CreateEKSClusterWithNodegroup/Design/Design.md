# AWS-CreateEKSClusterWithNodegroup

## What does this document do?

The AWS-CreateEKSClusterWithNodegroup runbook creates a new Amazon Elastic Kubernetes Service (EKS) control plane cluster with provisioned capacity provided by a nodegroup.

**NOTE**: In the event a resource (EKS Cluster or Nodegroup) fails its respective verification step, please validate if any resources were created and remove them if necessary.

## Input Parameters

### AutomationAssumeRole

- **Type**: AWS::IAM::Role::Arn
- **Description**: (Optional) The Amazon Resource Name (ARN) of the AWS Identity and Access Management (IAM) role that allows Systems Manager Automation to perform the actions on your behalf. If no role is specified, Systems Manager Automation uses the permissions of the user that starts this runbook.

### ClusterName

- **Type**: String
- **AllowedPattern**: `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,1023}$`
- **Description**: (Required) The unique name to give to your cluster.

### ClusterRoleArn

- **Type**: AWS::IAM::Role::Arn
- **Description**: (Required) The Amazon Resource Name (ARN) of the IAM role that provides permissions for the Kubernetes control plane to make calls to AWS API operations on your behalf. For more information, see [Amazon EKS Service IAM Role](https://docs.aws.amazon.com/eks/latest/userguide/service_IAM_role.html) in the Amazon EKS User Guide.

### NodegroupName

- **Type**: String
- **AllowedPattern**: `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,1023}$`
- **Description**: (Required) The unique name to give your nodegroup.

### NodegroupRoleArn

- **Type**: AWS::IAM::Role::Arn
- **Description**: (Required) The Amazon Resource Name (ARN) of the IAM role to associate with your nodegroup. The Amazon EKS worker node kubelet daemon makes calls to AWS APIs on your behalf. Nodes receive permissions for these API calls through an IAM instance profile and associated policies. Before you can launch nodes and register them into a cluster, you must create an IAM role for those nodes to use when they are launched. For more information, see [Amazon EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) in the Amazon EKS User Guide.

### SubnetIds

- **Type**: StringList
- **AllowedPattern**: `^subnet-[a-z0-9]{1,1017}$`
- **Description**: (Required) Subnets for your Amazon EKS nodes. Amazon EKS creates cross-account elastic network interfaces in these subnets to allow communication between your nodes and the Kubernetes control plane. You must specify at least two subnet IDs.

### EKSEndpointPrivateAccess

- **Type**: Boolean
- **Default**: true
- **Description**: (Optional) Set this value to true to enable private access for your cluster's Kubernetes API server endpoint. If you enable private access, Kubernetes API requests from within your cluster's VPC use the private VPC endpoint. If you disable private access and you have nodes or AWS Fargate pods in the cluster, then ensure that publicAccessCidrs includes the necessary CIDR blocks for communication with the nodes or Fargate pods. For more information, see [Amazon EKS cluster endpoint access control](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html) in the Amazon EKS User Guide.

### EKSEndpointPublicAccess

- **Type**: Boolean
- **Default**: false
- **Description**: (Optional) Set this value to false to disable public access to your cluster's Kubernetes API server endpoint. If you disable public access, your cluster's Kubernetes API server can only receive requests from within the cluster VPC. For more information, see [Amazon EKS cluster endpoint access control](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html) in the Amazon EKS User Guide.

### PublicAccessCIDRs

- **Type**: StringList
- **AllowedPattern**: `^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}$`
- **Default**: []
- **Description**: (Optional) The CIDR blocks that are allowed access to your cluster's public Kubernetes API server endpoint. Communication to the endpoint from addresses outside of the CIDR blocks that you specify is denied. If you've disabled private endpoint access and you have nodes or AWS Fargate pods in the cluster, then ensure that you specify the necessary CIDR blocks. For more information, see [Amazon EKS cluster endpoint access control](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html) in the Amazon EKS User Guide.

### SecurityGroupIds

- **Type**: StringList
- **AllowedPattern**: `^sg-[a-z0-9]{1,1021}$`
- **Default**: []
- **Description**: (Optional) Specify one or more security groups for the cross-account elastic network interfaces that Amazon EKS creates to use that allow communication between your nodes and the Kubernetes control plane. If you don't specify any security groups, then familiarize yourself with the difference between Amazon EKS defaults for clusters deployed with Kubernetes. For more information, see [Amazon EKS security group considerations](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html) in the Amazon EKS User Guide.

## Required IAM Permissions

The `AutomationAssumeRole` parameter requires the following actions to use the runbook successfully.

- `ssm:StartAutomationExecution`
- `ssm:GetAutomationExecution`
- `ec2:DescribeSubnets`
- `eks:CreateCluster`
- `eks:CreateNodegroup`
- `eks:DescribeCluster`
- `eks:DescribeNodegroup`
- `iam:CreateServiceLinkedRole`
- `iam:GetRole`
- `iam:ListAttachedRolePolicies`
- `iam:PassRole`

## Output Parameters

- CreateEKSCluster.CreateClusterResponse
- CreateNodegroup.CreateNodegroupResponse

## Document Steps

1. CreateEKSCluster (aws:executeAwsApi): Creates an Amazon EKS control plane.
   1. Inputs:
      1. Service: eks
      2. Api: CreateCluster
      3. name: The unique name to give to your cluster.
      4. roleArn: The Amazon Resource Name (ARN) of the IAM role that provides permissions for the Kubernetes control plane to make calls to AWS API operations on your behalf.
      5. resourcesVpcConfig: The VPC configuration that's used by the cluster control plane.
         1. EndpointPrivateAccess: Set this value to true to enable private access for your cluster's Kubernetes API server endpoint.
         2. EndpointPublicAccess: Set this value to false to disable public access to your cluster's Kubernetes API server endpoint.
         3. PublicAccessCidrs: The CIDR blocks that are allowed access to your cluster's public Kubernetes API server endpoint.
         4. SecurityGroupIds: Specify one or more security groups for the cross-account elastic network interfaces that Amazon EKS creates to use that allow communication between your nodes and the Kubernetes control plane.
         5. SubnetIds: Specify subnets for your Amazon EKS nodes. Amazon EKS creates cross-account elastic network interfaces in these subnets to allow communication between your nodes and the Kubernetes control plane.
   2. Outputs:
      1. CreateClusterResponse: Response received from the CreateCluster API call.
         1. Type: StringMap

2. VerifyEKSClusterIsActive (aws:waitForAwsResourceProperty): Verifies the cluster has reached the ACTIVE state.
   1. Inputs:
      1. Service: eks
      2. Api: DescribeCluster
      3. name: The name of the cluster to describe.
      4. PropertySelector: $.cluster.status
      5. DesiredValues:
         - ACTIVE
   2. IsCritical: true

3. CreateNodegroup (aws:executeAwsApi): Creates a managed nodegroup for an Amazon EKS cluster.
   1. Inputs:
      1. Service: eks
      2. Api: CreateNodegroup
      3. name: The name of the cluster to create the nodegroup in.
      4. nodegroupName: The unique name to give your nodegroup.
      5. nodeRole: The Amazon Resource Name (ARN) of the IAM role to associate with your nodegroup.
   2. Outputs:
      1. CreateNodegroupResponse: Response received from the CreateNodegroup API call.
         1. Type: StringMap

4. VerifyNodegroupIsActive (aws:waitForAwsResourceProperty): Verifies the nodegroup has reached the ACTIVE state.
   1. Inputs:
      1. Service: eks
      2. Api: DescribeNodegroup
      3. name: The name of the Amazon EKS cluster associated with the nodegroup.
      4. nodegroupName: The name of the nodegroup to describe.
      5. PropertySelector: $.nodegroup.status
      6. DesiredValues:
         - ACTIVE
   2. IsCritical: true

## Tests

### Test Case 1: Create an EKS Cluster and associated Nodegroup

Create an EKS Cluster with provisioned compute capacity provided by a nodegroup and verify their successful creation.

1. Launch CloudFormation stack which provisions prerequisite resources for the EKS Cluster and associated nodegroup.
2. Execute automation document using resources provisioned by CloudFormation as the input.
3. Verify successful document execution.

### Test Case 2: Create an EKS Cluster with the name of an existing cluster

Create an EKS Cluster with the name of one which already exists and verify runbook failure.

1. Launch CloudFormation stack which provisions prerequisite resources for the EKS cluster and associated nodegroup
2. Execute an API call to create an EKS cluster
3. Execute automation document using resources provisioned by CloudFormation and the name of the previously created EKS cluster as the input.
4. Verify failed document execution

### Test Case 3: Create an EKS Cluster and associated Nodegroup with a non-existent Nodegroup Role ARN

Create an EKS Cluster with a Nodegroup using a non-existent Nodegroup Role ARN and verify runbook failure.

1. Launch CloudFormation stack which provisions prerequisite resources for EKS cluster and associated nodegroup
2. Generate a non-existent IAM Role ARN and verify it does not exist.
3. Execute automation document using resources provisioned by the CloudFormation template and the non-existent role ARN as the input.
4. Verify failed document
