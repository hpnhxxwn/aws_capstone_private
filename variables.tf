# From your `~/.aws/credentials
variable "access_key" {
    default = "AKIAIHLG4M5TDP77XTRQ"
}

# From your `~/.aws/credentials
variable "secret_key" {
    default = "upSnWNY4wAmQizpvY5Mpid0E93dIv/GcOVprAt5i"
}

# Can be overridden if necessary
variable "region" {
  default = "us-west-2"
}

variable "amis" {
  type = "map"

  default = {
    us-east-1 = "ami-c7c5d4be"
    us-west-2 = "ami-c7c5d4be"
  }
}

# Path to your EC2 secret key
variable "pem_path" {
    default = "~/aws_sg/oregon_game_recommender.pem"
}

# The name of your EC2 key
variable "key_name" {
    default = "oregon_game_recommender"
}

# Location to dump EMR logs
variable "s3_uri" {
    default = "s3://yuanyuantiancai"
}

variable "copy_bucket" {
    default = "s3://yuanyuantiancai"
}

variable "service_image" {
    default = "ami-835b4efa"
}

#variable "ecs_service_role" {}
