#!/bin/bash
# Jenkins Installation Script for Ubuntu
# Run this script with: sudo bash install_jenkins.sh

set -e
set -o pipefail

echo "=========================================="
echo "Jenkins Installation Script for Ubuntu"
echo "=========================================="
echo "Tip: if your network requires proxy, run with: sudo -E bash install_jenkins.sh"

KEY_URL="https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key"
KEY_FILE="/usr/share/keyrings/jenkins-keyring.asc"

diagnose_jenkins_key_download() {
  echo ""
  echo "[ERROR] Failed to download Jenkins repository key."
  echo "[DIAG] Proxy env (current sudo shell):"
  env | grep -Ei '^(http_proxy|https_proxy|no_proxy)=' || echo "(not set)"
  echo "[DIAG] DNS lookup for pkg.jenkins.io:"
  getent hosts pkg.jenkins.io || echo "DNS lookup failed"
  echo "[DIAG] HTTPS HEAD request (10s timeout):"
  timeout 10s curl -I -v "$KEY_URL" | cat || echo "HEAD request failed or timed out"
  echo "[HINT] If you are behind a proxy, use: sudo -E bash install_jenkins.sh"
  echo ""
}

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
mkdir -p /usr/share/keyrings
if ! curl -fL --connect-timeout 10 --max-time 60 --retry 3 --retry-delay 2 \
  "$KEY_URL" \
  -o "$KEY_FILE"; then
  diagnose_jenkins_key_download
  exit 1
fi

echo "deb [signed-by=$KEY_FILE]" \
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
printf '%s\n' "=========================================="
printf '%s\n' "Jenkins installation completed!"
printf '%s\n' "=========================================="
printf '\n'
printf '%s\n' "Access Jenkins at: http://localhost:8080"
printf '\n'
printf '%s\n' "Initial Admin Password:"
cat /var/lib/jenkins/secrets/initialAdminPassword
printf '\n'
printf '%s\n' "=========================================="
printf '\n'
printf '%s\n' "Next steps:"
printf '%s\n' "1. Open http://localhost:8080 in your browser"
printf '%s\n' "2. Enter the initial admin password shown above"
printf '%s\n' "3. Install suggested plugins"
printf '%s\n' "4. Create your admin user"
printf '%s\n' "5. Install additional plugins: Email Extension Plugin"
printf '%s\n' "=========================================="
