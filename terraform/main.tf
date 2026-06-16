terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "kubernetes" {
  host                   = aws_eks_cluster.recommendation.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.recommendation.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.recommendation.token
}

# VPC
resource "aws_vpc" "recommendation" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "recommendation-vpc"
  }
}

# Subnets
resource "aws_subnet" "recommendation_public" {
  count                   = 2
  vpc_id                  = aws_vpc.recommendation.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "recommendation-public-subnet-${count.index}"
  }
}

resource "aws_subnet" "recommendation_private" {
  count             = 2
  vpc_id            = aws_vpc.recommendation.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "recommendation-private-subnet-${count.index}"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "recommendation" {
  vpc_id = aws_vpc.recommendation.id

  tags = {
    Name = "recommendation-igw"
  }
}

# EKS Cluster
resource "aws_eks_cluster" "recommendation" {
  name            = "recommendation-cluster"
  version         = "1.28"
  role_arn        = aws_iam_role.eks_cluster_role.arn
  vpc_config {
    subnet_ids = concat(
      aws_subnet.recommendation_public[*].id,
      aws_subnet.recommendation_private[*].id
    )
  }

  tags = {
    Name = "recommendation-cluster"
  }
}

# EKS Node Group
resource "aws_eks_node_group" "recommendation" {
  cluster_name    = aws_eks_cluster.recommendation.name
  node_group_name = "recommendation-nodes"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = aws_subnet.recommendation_private[*].id

  scaling_config {
    desired_size = 3
    max_size     = 10
    min_size     = 1
  }

  instance_types = ["t3.xlarge"]

  tags = {
    Name = "recommendation-node-group"
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "recommendation" {
  identifier       = "recommendation-db"
  engine           = "postgres"
  engine_version   = "15.3"
  instance_class   = "db.r6i.xlarge"
  allocated_storage = 100
  storage_type     = "gp3"

  db_name  = "recommendations_db"
  username = "admin"
  password = random_password.db_password.result

  multi_az               = true
  publicly_accessible    = false
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.recommendation.name

  backup_retention_period = 30
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = {
    Name = "recommendation-db"
  }
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "recommendation" {
  cluster_id           = "recommendation-redis"
  engine               = "redis"
  node_type            = "cache.r7g.xlarge"
  num_cache_nodes      = 3
  parameter_group_name = "default.redis7"
  port                 = 6379

  automatic_failover_enabled = true
  multi_az_enabled           = true
  security_group_ids         = [aws_security_group.elasticache.id]
  subnet_group_name          = aws_elasticache_subnet_group.recommendation.name

  tags = {
    Name = "recommendation-redis"
  }
}

# MSK Kafka Cluster
resource "aws_msk_cluster" "recommendation" {
  cluster_name           = "recommendation-kafka"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = "kafka.m6i.xlarge"
    client_subnets  = aws_subnet.recommendation_private[*].id
    security_groups = [aws_security_group.msk.id]

    storage_info {
      ebs_storage_info {
        volume_size = 100
      }
    }
  }

  tags = {
    Name = "recommendation-kafka"
  }
}

# S3 Bucket for models and artifacts
resource "aws_s3_bucket" "recommendation_artifacts" {
  bucket = "recommendation-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "recommendation-artifacts"
  }
}

resource "aws_s3_bucket_versioning" "recommendation_artifacts" {
  bucket = aws_s3_bucket.recommendation_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "recommendation" {
  name              = "/aws/recommendation-system"
  retention_in_days = 30

  tags = {
    Name = "recommendation-logs"
  }
}

# Outputs
output "eks_cluster_endpoint" {
  value       = aws_eks_cluster.recommendation.endpoint
  description = "EKS cluster endpoint"
}

output "rds_endpoint" {
  value       = aws_db_instance.recommendation.endpoint
  description = "RDS endpoint"
}

output "elasticache_endpoint" {
  value       = aws_elasticache_cluster.recommendation.cache_nodes[0].address
  description = "ElastiCache Redis endpoint"
}

output "msk_broker_nodes" {
  value       = aws_msk_cluster.recommendation.bootstrap_brokers
  description = "MSK bootstrap brokers"
}
