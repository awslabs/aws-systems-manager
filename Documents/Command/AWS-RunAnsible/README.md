# Configure SSM Agent CloudWatch Logging

Use this document to run Ansible playbooks on Amazon EC2 managed instances. Specify either playbook YAML text, playbook URL, or URL. If you specify multiple values, precedence order is: url, PlaybookURL, and then playbook. If you specify URL, everything from that point and below in S3 will be synced to the local machine (including any roles and custom modules). Use PlaybookFile for the playbook to run from that URL. Use the extravar parameter to send runtime variables to the Ansible execution. Use the check parameter to perform a dry run of the Ansible execution. The output of the dry run shows the changes that will be made when the playbook is executed. This version also supports zip files via http or s3 URLs. It also supports providing an s3 URL for a directory containing the playbook files.

## Type of Document

*Command* Document - Can be used with Run Command and State Manager

## Supported Platforms

Supported for *Linux*

## Supported SSM Agent Versions

Agent Version 2.0.902.0 and above

## Parameters

### playbook

Specify YAML code of the playbook that Ansible automation will execute. If you don't specify a URL, then you must specify playbook YAML in this field. Use this option for simple playbooks that dont require roles or other features better suited for complex playbooks.

### PlaybookURL

If you don''t specify playbook YAML, then you must specify a URL where the playbook is stored. This url can refer to a playbook yaml file, an s3 prefix, or an archive (TAR GZIP/BZIP2, Zip) containing all your playbook artifacts. You can specify the URL in the following formats: http://example.com/playbook.yml or s3://examplebucket/playbook.url. You can also specify an s3 URL for a directory containing the playbooks like s3://mybucket/myplabooks/.  For security reasons, you can''t specify a URL with quotes.

### PlaybookFile

The playbook file to run (including relative path), when specifying a playbook bundle like a zip file or an s3 path to a folder in a bucket

### extravars

Additional variables to pass to Ansible at runtime. Enter a space separated list of key/value pairs. For example: color=red flavor=lime

### WorkingDirectory

Current working directory to use for execution; if not specified, use random temp directory.

### check

Use the check parameter to perform a dry run of the Ansible execution

### verbose

Set the level of verbosity for logging the execution of the playbook. -v for low verbosity, -vvvv for debug level.

## Details

This document can be used to execute Ansible automation using SSM. The playbooks can be located on a web server, and s3 bucket or can be provided in simple YAML code. The automation will check if Ansible is installed and if is not it will install along with some dependencies.

## Dependencies
The automation will install Ansible if not found
