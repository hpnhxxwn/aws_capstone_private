# AWS Settings
aws = {
  region         = "us-east-1"
  key_name       = "cs502keyPair"                              # TODO
  ami            = "ami-5e0a3648"                       # TODO
  subnet_id      = "subnet-34c17e18"
  route53_zone   = "Z1CJE3YX1DH6JD"                     # TODO
  vpc_id         = "vpc-9e03bfe7"                       # TODO
  associate_public_ip_address = "true"
  in_ssh_cidr_block    = "0.0.0.0/0"
  monitoring = "false"
  iam_instance_profile = "Stock-EC2-Instance-Profile"    # TODO
  use_load_balancer = false
}

# S3 Settings
bucket = {
  log_uri = "s3://stock-cs502/emr-logs"
  config_uri = "s3://stock-cs502/config"
}

# Terraform Settings
terraform = {
  backend = "s3"
  region  = "us-east-1"
  bucket  = "stock-cs502" # TODO
}

# Tags
tags = {
  environment = "demo"
  user        = "jason"
}

# Web Server Settings
webserver = {
  instance_type        = "t2.micro"
  # create 2 web server for ELB
  count                = "1"
  root_volume_type     = "gp2"
  root_volume_size     = "8"
  root_volume_delete   = "true"
  in_http_cidr_block   = "0.0.0.0/0"
}

# emr cluster Settings
emr = {
  release = "emr-5.2.0"
  app = ["Hadoop", "Spark", "Hive"]
  master_type = "m3.xlarge"
  core_type = "m3.xlarge"
  core_count = "2"
  cidr_block = "0.0.0.0/0"
  iamRole = "EMR_DefaultRole"
}

