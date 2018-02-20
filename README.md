# AWS Systems Manager
Welcome to the Systems Manager community! Systems Manager allows you to automate common administrative tasks across resources on AWS and on-premises. Using Systems Manager, you can group resources by application and automate operational tasks on those resources. For example, you can remotely manage, collect inventory, patch, and configure your grouped resources.

## New to Systems Manager?
Here are some resources for you to get started with Systems Manager:

* [Getting Started](https://docs.aws.amazon.com/systems-manager/latest/userguide/what-is-systems-manager.html) documentation
* Blogposts on the [AWS Blog](https://aws.amazon.com/blogs/aws/category/management-tools/amazon-ec2-systems-manager/) and the [AWS Management Tools Blog](https://aws.amazon.com/blogs/mt/category/management-tools/amazon-ec2-systems-manager/) 
* The SSM Agent is also open sourced on GitHub [here](https://github.com/aws/amazon-ssm-agent) 

## Structure
The repository has top level folders that include:

* Documents: Contains Automation and Command type Documents. Each Document is a separate folder under the respective Document type
* Compliance: Contains InSpec profiles and other compliance scripts that you can use with Systems Manager
* Inventory: Contains custom gatherers that you can use with the Inventory service
* Examples: Any artifact that does not fit into the other categories will be a separate folder for that artifact

## Developing and Contributing
Contributions are welcome! The goal of the project is for developers to provide artifacts, documentation, and examples of product usage to share with the community. 

Please see the [CONTRIBUTING.md](https://github.com/awslabs/amazon-ssm/blob/master/CONTRIBUTING.md) file for more information.

## Legal and Licensing
This repository is licensed under the [MIT no attribution license](https://github.com/awslabs/amazon-ssm/blob/master/LICENSE).
