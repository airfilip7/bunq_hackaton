# Deploying bunq Nest to AWS EC2

Single EC2 instance running both frontend (nginx) and backend (FastAPI) via docker-compose. Cost: ~$15/month for t3.small.

## Prerequisites

- AWS CLI installed and configured (`aws configure`)
- An SSH key pair in your target region
- Your repo pushed to a git remote (GitHub/etc.)

---

## Step 1: Create IAM Role for EC2

The instance needs Bedrock access. Create a role with the right permissions.

```bash
# Create the trust policy
cat > /tmp/ec2-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create the role
aws iam create-role \
  --role-name bunq-nest-ec2 \
  --assume-role-policy-document file:///tmp/ec2-trust.json

# Attach Bedrock permissions
cat > /tmp/bedrock-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ],
    "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.*"
  }]
}
EOF

aws iam put-role-policy \
  --role-name bunq-nest-ec2 \
  --policy-name bedrock-access \
  --policy-document file:///tmp/bedrock-policy.json

# Create instance profile and attach role
aws iam create-instance-profile --instance-profile-name bunq-nest-ec2
aws iam add-role-to-instance-profile \
  --instance-profile-name bunq-nest-ec2 \
  --role-name bunq-nest-ec2

# Wait a few seconds for IAM propagation
sleep 10
```

## Step 2: Create Security Group

```bash
# Get your default VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)

# Create security group
SG_ID=$(aws ec2 create-security-group \
  --group-name bunq-nest-sg \
  --description "bunq Nest demo" \
  --vpc-id "$VPC_ID" \
  --query "GroupId" --output text)

# Open SSH (port 22) and HTTP (port 80)
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0

echo "Security Group: $SG_ID"
```

## Step 3: Launch EC2 Instance

```bash
# Find the latest Amazon Linux 2023 AMI
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" \
  --output text)

# Launch (t3.small = 2GB RAM, enough for Playwright/Chromium)
# Replace YOUR_KEY_NAME with your SSH key pair name
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type t3.small \
  --key-name YOUR_KEY_NAME \
  --security-group-ids "$SG_ID" \
  --iam-instance-profile Name=bunq-nest-ec2 \
  --metadata-options "HttpTokens=required,HttpPutResponseHopLimit=2" \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=bunq-nest-demo}]' \
  --query "Instances[0].InstanceId" --output text)

echo "Instance: $INSTANCE_ID"

# Wait for it to start
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

# Get the public IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query "Reservations[0].Instances[0].PublicIpAddress" --output text)

echo "Public IP: $PUBLIC_IP"
```

**Important:** `HttpPutResponseHopLimit=2` allows Docker containers to reach the instance metadata service for AWS credentials. Without this, Bedrock calls will fail.

## Step 4: Set Up the Instance

```bash
# SSH in
ssh -i ~/.ssh/YOUR_KEY_NAME.pem ec2-user@$PUBLIC_IP

# Clone the repo
git clone https://github.com/YOUR_USER/bunq_hackaton.git
cd bunq_hackaton

# Run the setup script (installs Docker, Compose, swap)
bash deploy/setup-ec2.sh

# Log out and back in for Docker group permissions
exit
```

```bash
# SSH back in
ssh -i ~/.ssh/YOUR_KEY_NAME.pem ec2-user@$PUBLIC_IP
cd bunq_hackaton

# Create your .env (only non-AWS vars — AWS creds come from the IAM role)
cat > .env << 'EOF'
AWS_REGION=us-east-1
BUNQ_API_KEY=your_bunq_sandbox_key_here
BUNQ_MODE=sandbox
FUNDA_MODE=
DEMO_REPLAY=0
EOF

# Deploy!
bash deploy/deploy.sh
```

Your app is now live at `http://<PUBLIC_IP>`.

## Updating After Code Changes

```bash
ssh -i ~/.ssh/YOUR_KEY_NAME.pem ec2-user@$PUBLIC_IP
cd bunq_hackaton
bash deploy/deploy.sh
```

That's it. The script pulls latest code and rebuilds containers.

## Useful Commands (on the instance)

```bash
# Shorthand (all commands use this)
COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file .env"

# View logs
$COMPOSE logs -f

# View only backend logs
$COMPOSE logs -f backend

# Restart everything
$COMPOSE restart

# Stop everything
$COMPOSE down

# Rebuild from scratch (if something is stuck)
$COMPOSE down
docker system prune -f
bash deploy/deploy.sh
```

## Cost Breakdown

| Resource | Cost |
|----------|------|
| t3.small (on-demand) | ~$15/month |
| 20GB gp3 EBS | ~$1.60/month |
| Data transfer (minimal for demo) | ~$0 |
| **Total** | **~$17/month** |

To save money: stop the instance when not demoing (`aws ec2 stop-instances --instance-ids $INSTANCE_ID`). You only pay for EBS storage when stopped (~$1.60/month). Start it again before the demo.

## Quick Console Alternative

If you prefer the AWS Console over CLI:

1. Go to **EC2 > Launch Instance**
2. Name: `bunq-nest-demo`
3. AMI: Amazon Linux 2023
4. Instance type: t3.small
5. Key pair: select or create one
6. Network: check "Allow HTTP traffic from the internet" and "Allow SSH"
7. Storage: 20 GiB gp3
8. Advanced > IAM instance profile: `bunq-nest-ec2` (create this first via IAM console with Bedrock permissions)
9. Advanced > Metadata version: V2 only (required), **Metadata response hop limit: 2**
10. Launch, then follow Step 4 above

## Troubleshooting

**"Cannot connect to http://IP"** — Check security group has port 80 open. Check containers are running: `docker compose -f deploy/docker-compose.prod.yml --env-file .env ps`.

**"Bedrock access denied"** — Verify the IAM role is attached: `curl http://169.254.169.254/latest/meta-data/iam/security-credentials/`. Verify Bedrock model access is enabled in the AWS Console (Bedrock > Model access).

**"OOM killed"** — Instance ran out of memory. Check swap is active: `free -h`. If not, re-run the swap creation from setup-ec2.sh.

**"Container can't pull images"** — Instance needs internet access. Ensure it's in a public subnet with an internet gateway (default VPC subnets have this).

**Frontend shows blank page** — Check nginx logs: `$COMPOSE logs nginx`. Usually a build error in the frontend build stage.
