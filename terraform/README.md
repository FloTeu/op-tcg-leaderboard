# init terraform
```
# coldstart
terraform init -backend-config="bucket=<terraform_bucket>" -reconfigure

terraform init
```

# setup variables
copy `terraform.tfvars.template` to `terraform.tfvars` and populate values.

# create infrastructure
```
sh terraform_apply.sh
```
