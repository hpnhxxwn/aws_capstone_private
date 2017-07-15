# Copyright 2017, Jason Zhu <jasonzhu810@gmail.com>
# All rights reserved.

# Terraform Configurations

variable "aws" {
    type = "map"
    default = {
        region          = ""
        key_name        = ""
        ami             = ""
        subnet_id       = ""
        route53_zone    = ""
        vpc_id          = ""
        security_group  = ""
        associate_public_ip_address = ""
        iam_instance_profile = ""
        in_ssh_cidr_block = ""
        use_load_balancer = ""
    }
}

variable "bucket" {
    type = "map"
    default = {
        log_uri = ""
        config_uri  = ""
    }
}


variable "emr" {
    type = "map"
    default = {
        release     = ""
        app         = ""
        master_type = ""
        core_type   = ""
        core_count  = ""
        cidr_block  = ""
        iamRole = ""
    }
}

variable "terraform" {
    type = "map"
    default = {
        backend = ""
        region  = ""
        bucket  = ""
    }
}

variable "tags" {
    type = "map"
    default = {
        environment = ""
        user        = ""
    }
}

variable "webserver" {
    type = "map"
    default = {
        instance_type        = ""
        count                = ""
        root_volume_type     = ""
        root_volume_size     = ""
        root_volume_delete   = ""
        in_http_cidr_block   = ""
    }
}




provider "aws" {
    region = "${var.aws["region"]}"
}

### EC2 Resources ###

# Web Server
resource "aws_instance" "webserver" {
    ami                         = "${var.aws["ami"]}"
    vpc_security_group_ids      = [ "${aws_security_group.default.id}", "${aws_security_group.webserver.id}" ]
    subnet_id                   = "${var.aws["subnet_id"]}"
    key_name                    = "${var.aws["key_name"]}"
    monitoring                  = "${var.aws["monitoring"]}"
    associate_public_ip_address = "${var.aws["associate_public_ip_address"]}"
    iam_instance_profile        = "${var.aws["iam_instance_profile"]}"

    instance_type               = "${var.webserver["instance_type"]}"
    count                       = "${var.webserver["count"]}"

    root_block_device {
        volume_type = "${var.webserver["root_volume_type"]}"
        volume_size = "${var.webserver["root_volume_size"]}"
        delete_on_termination = "${var.webserver["root_volume_delete"]}"
    }

    tags {
        Environment = "${var.tags["environment"]}"
        User        = "${var.tags["user"]}"
        Group       = "webserver"
        Name        = "webserver${count.index}"
    }
}


# https://www.terraform.io/docs/providers/aws/r/emr_cluster.html
resource "aws_emr_cluster" "emr-spark-cluster" {
  name          = "emr-spark-cluster"
  #release_label = "${var.emr["release"]}"         
  #applications  = "${var.emr["app"]}"
  release_label = "emr-5.2.0"         
  applications  = ["Hadoop", "Spark", "Hive"]

  ec2_attributes {
    key_name         = "${var.aws["key_name"]}"
    subnet_id        = "${var.aws["subnet_id"]}"
    instance_profile = "${var.aws["iam_instance_profile"]}"
    emr_managed_master_security_group = "${aws_security_group.sg.id}"
    emr_managed_slave_security_group  = "${aws_security_group.sg.id}"
    # service_access_security_group = "sg-1e1af364"
  }

  #master_instance_type = "${var.emr["master_type"]}"
  #core_instance_type   = "${var.emr["core_type"]}"
  #core_instance_count  = "${var.emr["core_count"]}"  # Increase as needed.
  master_instance_type = "m3.xlarge"
  core_instance_type   = "m3.xlarge"
  core_instance_count  = "2"
  # log_uri              = "${var.bucket["log_uri"]}"

  # This is the effect of `aws emr create-cluster --use-default-roles`.
  service_role = "EMR_DefaultRole"

  # These can be altered freely, they don't affect the config.
  tags {
    name = "emr-security-group-${var.tags["environment"]}"
    User        = "${var.tags["user"]}"
    Group       = "emr"
    Environment = "${var.tags["environment"]}"
  }

  # bootstrap_action {
    # path = "s3://elasticmapreduce/bootstrap-actions/run-if"
    # name = "runif"
    # args = ["instance.isMaster=true", "echo running on master node"]
  #}

  # configurations = "test-fixtures/emr_configurations.json"

  # This is the effect of `aws emr create-cluster --use-default-roles`.
  # service_role = "EMR_DefaultRole"

  # Spark YARN config to S3 for the ECS cluster to grab.
  #provisioner "remote-exec" {
   # inline = [
   #   "aws s3 cp /etc/hadoop/conf/core-site.xml ${var.bucket["config_uri"]}",
   #   "aws s3 cp /etc/hadoop/conf/yarn-site.xml ${var.bucket["config_uri"]}",
   # ]

    # Necessary to massage settings the way AWS wants them.
    #connection {
    #  type        = "ssh"
    #  user        = "hadoop"
    # user        = "root"
    #  host        = "${aws_emr_cluster.emr-spark-cluster.master_public_dns}"
    # private_key = "${file("${var.pem_path}")}"
    #}
  #}
}


### Security Groups ###

resource "aws_security_group" "default" {
    vpc_id = "${var.aws["vpc_id"]}"
    name = "default-security-group-${var.tags["environment"]}"
    description = "default security group in ${var.tags["environment"]}"

    # Allow all traffic within the default group
    ingress {
        from_port = 0
        to_port = 0
        protocol = "-1"
        self = "true"
    }
    egress {
        from_port = 0
        to_port = 0
        protocol = "-1"
        self = "true"
    }

    # Allow inbound SSH
    ingress {
        from_port = 22
        to_port = 22
        protocol = "tcp"
        cidr_blocks = ["${var.aws["in_ssh_cidr_block"]}"]
    }

    # Allow all outbound
    egress {
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags {
        Environment = "${var.tags["environment"]}"
        Name        = "default-security-group-${var.tags["environment"]}"
    }
}

resource "aws_security_group" "webserver" {
    vpc_id = "${var.aws["vpc_id"]}"
    name = "webserver-security-group-${var.tags["environment"]}"
    description = "webserver security group in ${var.tags["environment"]}"

    // allow inbound HTTP
    # comment below for ELB using 5006 port only
    ingress {
        from_port = 80
        to_port = 80
        protocol = "tcp"
        cidr_blocks = [ "${var.webserver["in_http_cidr_block"]}" ]
    }

    ingress {
        from_port = 5006
        to_port = 5006
        protocol = "tcp"
        cidr_blocks = [ "${var.webserver["in_http_cidr_block"]}" ]
    }

    tags {
        Environment = "${var.tags["environment"]}"
        User        = "${var.tags["user"]}"
        Name = "webserver-security-group-${var.tags["environment"]}"
    }
}

# what's protocal # https://www.terraform.io/docs/providers/aws/r/security_group.html
resource "aws_security_group" "sg" {
  name        = "emr cluster group"
  description = "Allow all inbound traffic"
  vpc_id      = "${var.aws["vpc_id"]}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    # cidr_blocks = [ "${var.emr["cidr_block"]}" ]
    cidr_blocks = [ "0.0.0.0/0" ]
  }

  # need to narrow down protocal and ports
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # depends_on = [ "${var.aws["subnet_id"]}" ]

  lifecycle {
    ignore_changes = ["ingress", "egress"]
  }

  tags {
        Environment = "${var.tags["environment"]}"
        Name        = "emr-cluster-security-group-${var.tags["environment"]}"
    }
}


### Route 53 Records ###
resource "aws_route53_record" "webserver" {
    zone_id = "${var.aws["route53_zone"]}"
    count   = "${var.webserver["count"]}"
    name    = "${element(aws_instance.webserver.*.tags.Name, count.index)}"
    type    = "A"
    ttl     = "300"
    records = ["${element(aws_instance.webserver.*.public_ip, count.index)}"]
}

resource "aws_route53_record" "stock" {
    zone_id = "${var.aws["route53_zone"]}"
    count   = "${(! var.aws["use_load_balancer"] && var.webserver["count"] > 0) ? 1 : 0}"
    name    = "web"
    type    = "CNAME"
    ttl     = "300"
    records = ["${element(aws_route53_record.webserver.*.fqdn, 0)}"]
}


#resource "aws_route53_record" "emr-cluster" {
#    zone_id = "${var.aws["route53_zone"]}"
#    count   = 1
#    name    = "master"
#    type    = "A"
#    ttl     = "300"
#    records = ["${aws_emr_cluster.emr-spark-cluster.master_public_dns}, count.index)}"]
#}

#resource "aws_vpc" "main" {
#  cidr_block           = "172.31.0.0/16"
#  enable_dns_hostnames = true

#  tags {
#    name = "emr_test"
#  }
#}

#resource "aws_subnet" "main" {
#  vpc_id     = "${aws_vpc.main.id}"
#  cidr_block = "172.31.0.0/20"

#  tags {
#    name = "emr_test"
#  }
#}

#resource "aws_internet_gateway" "gw" {
#  vpc_id = "${aws_vpc.main.id}"
#}

#resource "aws_route_table" "r" {
#  vpc_id = "${aws_vpc.main.id}"

#  route {
#    cidr_block = "0.0.0.0/0"
#    gateway_id = "${aws_internet_gateway.gw.id}"
#  }
#}

#resource "aws_main_route_table_association" "a" {
#  vpc_id         = "${aws_vpc.main.id}"
#  route_table_id = "${aws_route_table.r.id}"
#}

### Output ###
output "webservers"  {
    value = ["${aws_route53_record.webserver.*.fqdn}"]
}

output "emr_dns" {
  value = ["${aws_emr_cluster.emr-spark-cluster.master_public_dns}"]
}

