# prune-ami-lambda
AWS Lambda function to prune AMIs

Prune all AMIs older than X days that are not in use by a Launch Configuration, provided a minimum of Y exists.

| Environment Variable | Default   | Description                                                                                                                                      |
| -------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| aws_account_id       |           | The AWS account ID that AMIs will be pruned from                                                                                                 |
| aws_region           | eu-west-1 | The AWS region that AMIs will be pruned fro,                                                                                                     |
| node_types           |           | The node types to be pruned. The values set should correspond with the values for the AMI tag "nodetype"                                         |
| min_number_to_retain |           | The minimum number of images to be retained per nodetype.                                                                                        |
| min_days_to_retain   |           | The minimum number of days to keep images for, before considering them for evaluation                                                            |
| dry_run              |           | Set to false to disable dry run, otherwise set to true. If dry run is enabled the actions that would be taken will be output but not carried out |
