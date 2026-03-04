FROM jenkins/jenkins:lts

# Switch to root to install packages
USER root

# Install Python and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages globally
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Switch back to jenkins user
USER jenkins

# Skip initial setup wizard (optional, remove if you want the wizard)
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"

# Install suggested Jenkins plugins
RUN jenkins-plugin-cli --plugins \
    workflow-aggregator \
    git \
    email-ext \
    pipeline-utility-steps \
    credentials-binding

EXPOSE 8080 50000

VOLUME /var/jenkins_home
