# Simplified Terraform for AWS deployment - FIXED VERSION
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "enable_redis" {
  description = "Enable Redis ElastiCache for enhanced caching (adds ~$15/month)"
  type        = bool
  default     = false  # Default to false for cost savings
}

variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.t3.micro"  # Smallest for demo
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ecommerce-ml-platform"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-${count.index + 1}"
    Type = "Private"
  }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 101}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${count.index + 1}"
    Type = "Public"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# NAT Gateway
resource "aws_eip" "nat" {
  count  = 2
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip-${count.index + 1}"
  }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_nat_gateway" "main" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.project_name}-nat-${count.index + 1}"
  }

  depends_on = [aws_internet_gateway.main]
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table" "private" {
  count  = 2
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = {
    Name = "${var.project_name}-private-rt-${count.index + 1}"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# Security Groups
resource "aws_security_group" "redis" {
  count       = var.enable_redis ? 1 : 0  # Only create if Redis enabled
  name_prefix = "${var.project_name}-redis"
  vpc_id      = data.aws_vpc.default.id
  description = "Security group for Redis"

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Simplified for demo
    description = "Redis access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}


resource "aws_security_group" "kafka" {
  name_prefix = "${var.project_name}-kafka"
  vpc_id      = aws_vpc.main.id
  description = "Security group for Kafka MSK cluster"

  # Kafka broker communication
  ingress {
    from_port   = 9092
    to_port     = 9092
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Kafka broker port"
  }

  ingress {
    from_port   = 9094
    to_port     = 9094
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Kafka broker TLS port"
  }

  # Zookeeper
  ingress {
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Zookeeper port"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-kafka-sg"
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-redis"
  vpc_id      = aws_vpc.main.id
  description = "Security group for Redis ElastiCache"

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Redis port"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}

resource "aws_security_group" "ecs" {
  name_prefix = "${var.project_name}-ecs"
  vpc_id      = aws_vpc.main.id
  description = "Security group for ECS tasks"

  # HTTP traffic for ML API
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "ML API port"
  }

  # HTTPS traffic
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS port"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-ecs-sg"
  }
}

resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb"
  vpc_id      = aws_vpc.main.id
  description = "Security group for Application Load Balancer"

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP port"
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS port"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# S3 Data Lake
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project_name}-data-lake-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "Data Lake"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "data_lake_versioning" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake_encryption" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake_pab" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# MSK Kafka Cluster Configuration
resource "aws_msk_configuration" "kafka_config" {
  kafka_versions = ["3.4.0"]
  name           = "${var.project_name}-kafka-config"

  server_properties = <<PROPERTIES
auto.create.topics.enable=true
default.replication.factor=2
min.insync.replicas=1
num.partitions=3
log.retention.hours=168
log.segment.bytes=1073741824
PROPERTIES
}

# MSK Kafka Cluster
resource "aws_msk_cluster" "kafka" {
  cluster_name           = "${var.project_name}-kafka"
  kafka_version          = "3.4.0"
  number_of_broker_nodes = 2

  broker_node_group_info {
    instance_type  = "kafka.t3.small"
    client_subnets = aws_subnet.private[*].id
    
    storage_info {
      ebs_storage_info {
        volume_size = 20
      }
    }

    security_groups = [aws_security_group.kafka.id]
  }

  configuration_info {
    arn      = aws_msk_configuration.kafka_config.arn
    revision = aws_msk_configuration.kafka_config.latest_revision
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS_PLAINTEXT"
      in_cluster    = true
    }
  }

  tags = {
    Name        = "${var.project_name}-kafka"
    Environment = var.environment
  }
}

# KMS Key for MSK encryption
resource "aws_kms_key" "msk" {
  description = "KMS key for MSK cluster encryption"
  
  tags = {
    Name = "${var.project_name}-msk-key"
  }
}

resource "aws_kms_alias" "msk" {
  name          = "alias/${var.project_name}-msk"
  target_key_id = aws_kms_key.msk.key_id
}

# Redis ElastiCache Subnet Group
# resource "aws_elasticache_subnet_group" "redis" {
#   name       = "${var.project_name}-redis-subnet-group"
#   subnet_ids = aws_subnet.private[*].id

#   tags = {
#     Name = "${var.project_name}-redis-subnet-group"
#   }
# }

resource "aws_elasticache_subnet_group" "redis" {
  count      = var.enable_redis ? 1 : 0  # Only create if Redis enabled
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

# Redis ElastiCache Cluster
# resource "aws_elasticache_cluster" "redis" {
#   cluster_id           = "${var.project_name}-redis"
#   engine               = "redis"
#   node_type            = "cache.t3.micro"
#   num_cache_nodes      = 1
#   parameter_group_name = "default.redis7"
#   port                 = 6379
#   subnet_group_name    = aws_elasticache_subnet_group.redis.name
#   security_group_ids   = [aws_security_group.redis.id]

#   tags = {
#     Name        = "${var.project_name}-redis"
#     Environment = var.environment
#   }
# }

resource "aws_elasticache_cluster" "redis" {
  count                = var.enable_redis ? 1 : 0  # Only create if Redis enabled
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis[0].name
  security_group_ids   = [aws_security_group.redis[0].id]

  tags = {
    Name    = "${var.project_name}-redis"
    Purpose = "Feature Caching"
  }
}


# ECS Cluster
resource "aws_ecs_cluster" "ml_cluster" {
  name = "${var.project_name}-ml-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${var.project_name}-ecs"
    Environment = var.environment
  }
}

# ECR Repository
resource "aws_ecr_repository" "ml_api" {
  name                 = "${var.project_name}/ml-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-ecr"
    Environment = var.environment
  }
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Task
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task-role"
  }
}

# IAM Policy for ECS Task to access S3 and other services
resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${var.project_name}-ecs-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kafka:DescribeCluster",
          "kafka:GetBootstrapBrokers"
        ]
        Resource = aws_msk_cluster.kafka.arn
      }
    ]
  })
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name        = "${var.project_name}-alb"
    Environment = var.environment
  }
}

# ALB Target Group
resource "aws_lb_target_group" "ml_api" {
  name     = "${var.project_name}-ml-api-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-ml-api-tg"
  }
}

# ALB Listener
resource "aws_lb_listener" "ml_api" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ml_api.arn
  }

  tags = {
    Name = "${var.project_name}-alb-listener"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ml_api" {
  name              = "/ecs/${var.project_name}-ml-api"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-ml-api-logs"
    Environment = var.environment
  }
}

# Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "kafka_bootstrap_brokers" {
  description = "MSK bootstrap brokers"
  value       = aws_msk_cluster.kafka.bootstrap_brokers
}

output "kafka_bootstrap_brokers_tls" {
  description = "MSK bootstrap brokers (TLS)"
  value       = aws_msk_cluster.kafka.bootstrap_brokers_tls
}

output "s3_data_lake_bucket" {
  description = "S3 data lake bucket name"
  value       = aws_s3_bucket.data_lake.bucket
}

# output "redis_endpoint" {
#   description = "Redis endpoint"
#   value       = aws_elasticache_cluster.redis.cache_nodes[0].address
# }

# output "redis_port" {
#   description = "Redis port"
#   value       = aws_elasticache_cluster.redis.port
# }

output "redis_endpoint" {
  description = "Redis endpoint for feature caching (only if enabled)"
  value       = var.enable_redis ? aws_elasticache_cluster.redis[0].cache_nodes[0].address : "Redis not enabled - using in-memory cache"
}

output "redis_port" {
  description = "Redis port (only if enabled)"
  value       = var.enable_redis ? aws_elasticache_cluster.redis[0].port : "N/A"
}

output "redis_status" {
  description = "Redis deployment status"
  value       = var.enable_redis ? "Enabled" : "Disabled (cost optimization)"
}

# UPDATE deployment instructions output:
output "deployment_instructions" {
  description = "Next steps for deployment"
  value = <<-EOT
  🚀 Infrastructure created successfully! 
  
  Redis Status: ${var.enable_redis ? "✅ Enabled" : "⚠️ Disabled (cost optimization)"}
  
  ${var.enable_redis ? 
    "Redis Endpoint: ${aws_elasticache_cluster.redis[0].cache_nodes[0].address}" : 
    "Using in-memory caching - enable Redis with: terraform apply -var='enable_redis=true'"
  }
  
  1. Build and push Docker image:
     docker build -t ${aws_ecr_repository.ml_api.repository_url}:latest .
     aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.ml_api.repository_url}
     docker push ${aws_ecr_repository.ml_api.repository_url}:latest
  
  2. Update your application config:
     S3_BUCKET=${aws_s3_bucket.data_lake.bucket}
     ${var.enable_redis ? "REDIS_HOST=${aws_elasticache_cluster.redis[0].cache_nodes[0].address}" : "CACHE_STRATEGY=memory"}
  
  3. Deploy to ECS:
     Use the ECS cluster: ${aws_ecs_cluster.ml_cluster.name}
     
  💰 Estimated monthly cost: ${var.enable_redis ? "~$35-45" : "~$20-25"} (Redis ${var.enable_redis ? "enabled" : "disabled"})
  
  To enable Redis later: terraform apply -var='enable_redis=true'
  To disable Redis: terraform apply -var='enable_redis=false'
  
  EOT
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.ml_api.repository_url
}

output "load_balancer_dns" {
  description = "Load balancer DNS name"
  value       = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.ml_cluster.name
}

output "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task_role.arn
}