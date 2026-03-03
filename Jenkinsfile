/**
 * Jenkins Pipeline for Running Tests with Email Notification
 * 
 * This pipeline:
 * 1. Sets up Python virtual environment
 * 2. Installs dependencies
 * 3. Runs the test suite
 * 4. Collects failure information
 * 5. Sends email notification on failure
 */

pipeline {
    agent any
    
    // Schedule: Run daily at 8 AM (cron syntax)
    triggers {
        cron('0 8 * * *')  // Modify this schedule as needed
        // Examples:
        // cron('0 */2 * * *')  // Every 2 hours
        // cron('0 8,18 * * 1-5')  // 8 AM and 6 PM on weekdays
        // cron('H/30 * * * *')  // Every 30 minutes
    }
    
    environment {
        // Email configuration - Set these in Jenkins credentials or environment
        SMTP_SERVER = credentials('smtp-server') ?: 'smtp.gmail.com'
        SMTP_PORT = '587'
        SMTP_USER = credentials('smtp-user')
        SMTP_PASSWORD = credentials('smtp-password')
        EMAIL_SENDER = credentials('email-sender')
        EMAIL_RECIPIENTS = credentials('email-recipients')
        
        // Python virtual environment
        VENV_DIR = "${WORKSPACE}/venv"
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out source code...'
                checkout scm
            }
        }
        
        stage('Setup Python Environment') {
            steps {
                echo 'Setting up Python virtual environment...'
                sh '''
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }
        
        stage('Run Tests') {
            steps {
                echo 'Running test suite...'
                sh '''
                    . ${VENV_DIR}/bin/activate
                    python scripts/run_tests.py \
                        --test-dir tests \
                        --pattern "test_*.py" \
                        --output test_report.json
                '''
            }
            post {
                always {
                    // Archive the test report
                    archiveArtifacts artifacts: 'test_report.json', allowEmptyArchive: true
                }
            }
        }
        
        stage('Send Notification') {
            when {
                expression {
                    // Check if there are test failures
                    def report = readJSON file: 'test_report.json'
                    return !report.all_passed
                }
            }
            steps {
                echo 'Sending failure notification email...'
                sh '''
                    . ${VENV_DIR}/bin/activate
                    python scripts/send_email.py \
                        --report test_report.json \
                        --smtp-server ${SMTP_SERVER} \
                        --smtp-port ${SMTP_PORT} \
                        --smtp-user ${SMTP_USER} \
                        --smtp-password ${SMTP_PASSWORD} \
                        --sender ${EMAIL_SENDER} \
                        --recipients ${EMAIL_RECIPIENTS} \
                        --job-name "${JOB_NAME}" \
                        --build-number "${BUILD_NUMBER}" \
                        --build-url "${BUILD_URL}"
                '''
            }
        }
    }
    
    post {
        always {
            echo 'Pipeline completed.'
            // Clean up workspace (optional)
            // cleanWs()
        }
        success {
            echo 'All tests passed!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}
