# Marks AWS as a resource provider.
provider "aws" {
  access_key = "${var.access_key}"
  secret_key = "${var.secret_key}"
  region     = "${var.region}"
}

# `aws_emr_cluster` is built-in to Terraform. We name ours `emr-spark-cluster`.
resource "aws_emr_cluster" "emr-spark-cluster" {
  name          = "emr-spark-test"
  release_label = "emr-5.2.0"         # 2016 November
  applications  = ["Hadoop", "Spark", "Hive"]

  ec2_attributes {
    key_name         = "${var.key_name}"
    subnet_id        = "${aws_subnet.main.id}"
    instance_profile = "EMR_EC2_DefaultRole"
    emr_managed_master_security_group = "${aws_security_group.sg.id}"
    emr_managed_slave_security_group  = "${aws_security_group.sg.id}"
    # service_access_security_group = "sg-1e1af364"
  }

  master_instance_type = "m3.xlarge"
  core_instance_type   = "m3.xlarge"
  core_instance_count  = 2               # Increase as needed.
  log_uri              = "${var.s3_uri}"

  # These can be altered freely, they don't affect the config.
  tags {
    name = "Test Spark Cluster"
    role = "EMR_DefaultRole"
    env  = "env"
  }

  configurations = "spark-env.json"

  # This is the effect of `aws emr create-cluster --use-default-roles`.
  service_role = "EMR_DefaultRole"

  # Spark YARN config to S3 for the ECS cluster to grab.
  provisioner "remote-exec" {
    inline = [
      "aws s3 cp /etc/hadoop/conf/core-site.xml ${var.copy_bucket}",
      "aws s3 cp /etc/hadoop/conf/yarn-site.xml ${var.copy_bucket}",
    ]

    # Necessary to massage settings the way AWS wants them.
    connection {
      type        = "ssh"
      user        = "hadoop"
      host        = "${aws_emr_cluster.emr-spark-cluster.master_public_dns}"
      private_key = "${file("${var.pem_path}")}"
    }
  }
}

# Pipable to other programs.
output "emr_dns" {
  value = "${aws_emr_cluster.emr-spark-cluster.master_public_dns}"
}

# Security group
resource "aws_security_group" "sg" {
  name        = "allow_all"
  description = "Allow all inbound traffic"
  vpc_id      = "${aws_vpc.main.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  depends_on = ["aws_subnet.main"]

  lifecycle {
    ignore_changes = ["ingress", "egress"]
  }

  tags {
    name = "emr_test"
  }
}

resource "aws_vpc" "main" {
  cidr_block           = "172.31.0.0/16"
  enable_dns_hostnames = true

  tags {
    name = "emr_test"
  }
}

resource "aws_subnet" "main" {
  vpc_id     = "${aws_vpc.main.id}"
  cidr_block = "172.31.0.0/20"

  tags {
    name = "emr_test"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = "${aws_vpc.main.id}"
}

resource "aws_route_table" "r" {
  vpc_id = "${aws_vpc.main.id}"

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = "${aws_internet_gateway.gw.id}"
  }
}

resource "aws_main_route_table_association" "a" {
  vpc_id         = "${aws_vpc.main.id}"
  route_table_id = "${aws_route_table.r.id}"
}


#
# ECS Resources
#

# ECS cluster is only a name that ECS machines may join
resource "aws_ecs_cluster" "ecs-test" {
  lifecycle {
    create_before_destroy = true
  }

  name = "ecs-test"
}

# Template for container definition, allows us to inject environment
#data "template_file" "ecs_ecs-test_task" {
#  template = "${file("${path.module}/containers.json")}"

#  vars {
#    image = "${var.service_image}"
#  }
#}

# Allows resource sharing among multiple containers
#resource "aws_ecs_task_definition" "ecs-test-task" {
#  family                = "ecs-test"
#  container_definitions = "${data.template_file.ecs_ecs-test_task.rendered}"
#  depends_on            = ["aws_emr_cluster.emr-spark-cluster"]
#}

# Defines running an ECS task as a service
#resource "aws_ecs_service" "ecs-test" {
#  name                               = "ecs-test"
#  cluster                            = "${aws_ecs_cluster.ecs-test.id}"
#  task_definition                    = "${aws_ecs_task_definition.ecs-test-task.family}:${aws_ecs_task_definition.ecs-test-task.revision}"
#  desired_count                      = 1
#  deployment_minimum_healthy_percent = "0"                                                                                                 # allow old services to be torn down
#  deployment_maximum_percent         = "100"
#}
