#!/bin/bash

set -e

echo "🚀 Starting Simple EC2 deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    print_status "Checking requirements..."

    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi

    print_status "All requirements are met"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    print_status "Deploying infrastructure with Terraform..."

    cd infra

    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init

    # Plan the deployment
    print_status "Planning Terraform deployment..."
    terraform plan -var-file="environments/staging.tfvars" -out=staging.plan

    # Apply the plan
    print_status "Applying Terraform plan..."
    terraform apply staging.plan

    # Get the EC2 instance IP
    print_status "Getting EC2 instance IP..."
    INSTANCE_IP=$(terraform output -raw instance_public_ip)

    if [ -z "$INSTANCE_IP" ]; then
        print_error "Failed to get instance IP from Terraform output"
        exit 1
    fi

    print_status "EC2 instance IP: $INSTANCE_IP"
    echo "$INSTANCE_IP" > ../.instance_ip

    cd ..
}

# Wait for EC2 instance to be ready
wait_for_instance() {
    print_status "Waiting for EC2 instance to be ready..."

    INSTANCE_IP=$(cat .instance_ip)

    # Wait for SSH to be available
    print_status "Waiting for SSH to be available..."
    for i in {1..30}; do
        if ssh -i ~/.ssh/gitops-key -o ConnectTimeout=10 -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "echo 'SSH ready'" 2>/dev/null; then
            print_status "SSH is ready"
            break
        fi

        if [ $i -eq 30 ]; then
            print_error "SSH connection failed after 30 attempts"
            exit 1
        fi

        print_status "Attempt $i/30 - SSH not ready yet, waiting 10 seconds..."
        sleep 10
    done
}

# Deploy application using SSH
deploy_application() {
    print_status "Deploying application using SSH..."

    INSTANCE_IP=$(cat .instance_ip)

    # Create app directory on EC2
    print_status "Creating app directory on EC2..."
    ssh -i ~/.ssh/gitops-key -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "mkdir -p /home/ubuntu/app"

    # Copy Docker Compose file to EC2
    print_status "Copying Docker Compose file to EC2..."
    scp -i ~/.ssh/gitops-key -o StrictHostKeyChecking=no docker-compose.yml ubuntu@$INSTANCE_IP:/home/ubuntu/app/

    # Copy environment file to EC2
    print_status "Copying environment file to EC2..."
    scp -i ~/.ssh/gitops-key -o StrictHostKeyChecking=no env.example ubuntu@$INSTANCE_IP:/home/ubuntu/app/.env

    # Run deployment commands on EC2
    print_status "Running deployment commands on EC2..."
    ssh -i ~/.ssh/gitops-key -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
        cd /home/ubuntu/app
        
        # Stop existing containers
        echo "Stopping existing containers..."
        docker compose down || true
        
        # Remove old containers and images
        echo "Cleaning up old containers and images..."
        docker container prune -f
        docker image prune -f
        docker volume prune -f
        
        # Pull latest images
        echo "Pulling latest images..."
        docker compose pull
        
        # Start services
        echo "Starting services..."
        docker compose up -d
        
        # Wait for services to be ready
        echo "Waiting for services to be ready..."
        sleep 30
        
        # Check service status
        echo "Checking service status..."
        docker compose ps
EOF
}

# Health check
health_check() {
    print_status "Performing health check..."

    INSTANCE_IP=$(cat .instance_ip)

    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 60

    # Test each service
    SERVICES=(
        "http://$INSTANCE_IP:5001/health"
        "http://$INSTANCE_IP:5002/health"
        "http://$INSTANCE_IP:5003/health"
        "http://$INSTANCE_IP:8080/"
    )

    for service in "${SERVICES[@]}"; do
        print_status "Testing: $service"
        if curl -f -s "$service" > /dev/null; then
            print_status "✅ Service is healthy: $service"
        else
            print_warning "⚠️  Service might not be ready: $service"
        fi
    done
}

# Main execution
main() {
    print_status "Starting Simple EC2 deployment process..."

    check_requirements
    deploy_infrastructure
    wait_for_instance
    deploy_application
    health_check

    INSTANCE_IP=$(cat .instance_ip)
    print_status "🎉 Deployment completed successfully!"
    print_status "Frontend: http://$INSTANCE_IP:8080"
    print_status "User Service: http://$INSTANCE_IP:5001"
    print_status "Product Service: http://$INSTANCE_IP:5002"
    print_status "Order Service: http://$INSTANCE_IP:5003"
}

# Run main function
main "$@" 
