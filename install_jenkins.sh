#!/bin/bash
# Jenkins Installation Script for Ubuntu
# Run this script with: sudo bash install_jenkins.sh

set -e

echo "=========================================="
echo "Jenkins Installation Script for Ubuntu"
echo "=========================================="

# Update system packages
echo "[1/6] Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install Java (Jenkins requires Java 11 or 17)
echo "[2/6] Installing Java 17..."
apt-get install -y fontconfig openjdk-17-jre
java -version

# Add Jenkins repository key
echo "[3/6] Adding Jenkins repository..."
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | tee \
  /usr/share/keyrings/jenkins-keyring.asc > /dev/null

echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc]" \
  https://pkg.jenkins.io/debian-stable binary/ | tee \
  /etc/apt/sources.list.d/jenkins.list > /dev/null

# Install Jenkins
echo "[4/6] Installing Jenkins..."
apt-get update -y
apt-get install -y jenkins

# Install Python and pip for running tests
echo "[5/6] Installing Python and dependencies..."
apt-get install -y python3 python3-pip python3-venv

# Start and enable Jenkins service
echo "[6/6] Starting Jenkins service..."
systemctl enable jenkins
systemctl start jenkins

# Wait for Jenkins to start
echo "Waiting for Jenkins to start..."
sleep 30

# Get initial admin password
echo "=========================================="
echo "Jenkins installation completed!"
echo "=========================================="
echo ""
echo "Access Jenkins at: http://localhost:8080"
echo ""
echo "Initial Admin Password:"
cat /var/lib/jenkins/secrets/initialAdminPassword
echo ""
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Open http://localhost:8080 in your browser"
echo "2. Enter the initial admin password shown above"
echo "3. Install suggested plugins"
echo "4. Create your admin user"
echo "5. Install additional plugins: Email Extension Plugin"
echo "=========================================="
