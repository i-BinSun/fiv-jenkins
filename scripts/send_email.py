#!/usr/bin/env python3
"""
Email Notification Script for Test Failures

This script reads the test report JSON and sends an email notification
if there are any test failures.
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import argparse


def load_test_report(report_file):
    """Load the test report from JSON file"""
    with open(report_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_failure_html(failure):
    """Format a single failure as HTML"""
    return f"""
    <div style="margin-bottom: 20px; padding: 15px; background-color: #fff3f3; border-left: 4px solid #dc3545; border-radius: 4px;">
        <h3 style="color: #dc3545; margin: 0 0 10px 0;">{failure['test_name']}</h3>
        <table style="font-size: 14px; color: #333;">
            <tr>
                <td style="padding: 2px 10px 2px 0; font-weight: bold;">Class:</td>
                <td>{failure['test_class']}</td>
            </tr>
            <tr>
                <td style="padding: 2px 10px 2px 0; font-weight: bold;">Method:</td>
                <td>{failure['test_method']}</td>
            </tr>
            <tr>
                <td style="padding: 2px 10px 2px 0; font-weight: bold;">Error Type:</td>
                <td style="color: #dc3545;">{failure['error_type']}</td>
            </tr>
            <tr>
                <td style="padding: 2px 10px 2px 0; font-weight: bold;">Error Message:</td>
                <td>{failure['error_message']}</td>
            </tr>
        </table>
        <div style="margin-top: 10px;">
            <strong>Stack Trace:</strong>
            <pre style="background-color: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; line-height: 1.4;">{failure['stack_trace']}</pre>
        </div>
    </div>
    """


def format_error_html(error):
    """Format a single error as HTML"""
    return f"""
    <div style="margin-bottom: 20px; padding: 15px; background-color: #fff8e6; border-left: 4px solid #ffc107; border-radius: 4px;">
        <h3 style="color: #856404; margin: 0 0 10px 0;">{error['test_name']}</h3>
        <table style="font-size: 14px; color: #333;">
            <tr>
                <td style="padding: 2px 10px 2px 0; font-weight: bold;">Class:</td>
                <td>{error['test_class']}</td>
            </tr>
            <tr>
                <td style="padding: 2px 10px 2px 0; font-weight: bold;">Method:</td>
                <td>{error['test_method']}</td>
            </tr>
            <tr>
                <td style="padding: 2px 10px 2px 0; font-weight: bold;">Error Type:</td>
                <td style="color: #856404;">{error['error_type']}</td>
            </tr>
            <tr>
                <td style="padding: 2px 10px 2px 0; font-weight: bold;">Error Message:</td>
                <td>{error['error_message']}</td>
            </tr>
        </table>
        <div style="margin-top: 10px;">
            <strong>Stack Trace:</strong>
            <pre style="background-color: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; line-height: 1.4;">{error['stack_trace']}</pre>
        </div>
    </div>
    """


def create_email_body(report, job_name="", build_number="", build_url=""):
    """Create the HTML email body from the test report"""
    summary = report.get("summary", {})
    
    # Determine overall status
    if report.get("all_passed"):
        status_color = "#28a745"
        status_text = "ALL TESTS PASSED"
        status_bg = "#d4edda"
    else:
        status_color = "#dc3545"
        status_text = "TESTS FAILED"
        status_bg = "#f8d7da"
    
    # Build info section
    build_info = ""
    if job_name or build_number or build_url:
        build_info = f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #e9ecef; border-radius: 4px;">
            <h3 style="margin: 0 0 10px 0; color: #495057;">Build Information</h3>
            <table style="font-size: 14px;">
                {"<tr><td style='padding: 2px 10px 2px 0; font-weight: bold;'>Job Name:</td><td>" + job_name + "</td></tr>" if job_name else ""}
                {"<tr><td style='padding: 2px 10px 2px 0; font-weight: bold;'>Build Number:</td><td><a href='" + build_url + "'>#" + str(build_number) + "</a></td></tr>" if build_number and build_url else "<tr><td style='padding: 2px 10px 2px 0; font-weight: bold;'>Build Number:</td><td>#" + str(build_number) + "</td></tr>" if build_number else ""}
            </table>
        </div>
        """
    
    # Format failures
    failures_html = ""
    if report.get("failures"):
        failures_html = "<h2 style='color: #dc3545;'>Test Failures</h2>"
        for failure in report["failures"]:
            failures_html += format_failure_html(failure)
    
    # Format errors
    errors_html = ""
    if report.get("errors"):
        errors_html = "<h2 style='color: #856404;'>Test Errors</h2>"
        for error in report["errors"]:
            errors_html += format_error_html(error)
    
    # Create the full HTML email
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px;">
        
        <!-- Header -->
        <div style="text-align: center; padding: 20px; background-color: {status_bg}; border-radius: 8px; margin-bottom: 20px;">
            <h1 style="color: {status_color}; margin: 0;">{status_text}</h1>
            <p style="margin: 10px 0 0 0; color: #666;">Test Report - {report.get('timestamp', 'N/A')}</p>
        </div>
        
        {build_info}
        
        <!-- Summary -->
        <div style="margin-bottom: 20px; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
            <h2 style="margin: 0 0 15px 0; color: #495057;">Test Summary</h2>
            <table style="width: 100%; font-size: 16px;">
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="display: inline-block; width: 20px; height: 20px; background-color: #6c757d; border-radius: 50%; margin-right: 10px;"></span>
                        <strong>Total Tests:</strong>
                    </td>
                    <td style="text-align: right; font-size: 24px; font-weight: bold;">{summary.get('total', 0)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="display: inline-block; width: 20px; height: 20px; background-color: #28a745; border-radius: 50%; margin-right: 10px;"></span>
                        <strong>Passed:</strong>
                    </td>
                    <td style="text-align: right; font-size: 24px; font-weight: bold; color: #28a745;">{summary.get('passed', 0)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="display: inline-block; width: 20px; height: 20px; background-color: #dc3545; border-radius: 50%; margin-right: 10px;"></span>
                        <strong>Failed:</strong>
                    </td>
                    <td style="text-align: right; font-size: 24px; font-weight: bold; color: #dc3545;">{summary.get('failed', 0)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="display: inline-block; width: 20px; height: 20px; background-color: #ffc107; border-radius: 50%; margin-right: 10px;"></span>
                        <strong>Errors:</strong>
                    </td>
                    <td style="text-align: right; font-size: 24px; font-weight: bold; color: #ffc107;">{summary.get('errors', 0)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="display: inline-block; width: 20px; height: 20px; background-color: #17a2b8; border-radius: 50%; margin-right: 10px;"></span>
                        <strong>Skipped:</strong>
                    </td>
                    <td style="text-align: right; font-size: 24px; font-weight: bold; color: #17a2b8;">{summary.get('skipped', 0)}</td>
                </tr>
            </table>
            <p style="margin: 15px 0 0 0; color: #666; font-size: 14px;">
                Duration: {report.get('duration_seconds', 0):.2f} seconds
            </p>
        </div>
        
        <!-- Failures and Errors Details -->
        {failures_html}
        {errors_html}
        
        <!-- Footer -->
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; text-align: center; color: #666; font-size: 12px;">
            <p>This is an automated message from Jenkins CI</p>
            <p>Report generated at {report.get('timestamp', 'N/A')}</p>
        </div>
        
    </body>
    </html>
    """
    
    return html


def create_plain_text_body(report, job_name="", build_number="", build_url=""):
    """Create plain text email body as fallback"""
    summary = report.get("summary", {})
    
    lines = [
        "=" * 60,
        "TEST EXECUTION REPORT",
        "=" * 60,
        "",
        f"Timestamp: {report.get('timestamp', 'N/A')}",
        f"Duration: {report.get('duration_seconds', 0):.2f} seconds",
    ]
    
    if job_name:
        lines.append(f"Job Name: {job_name}")
    if build_number:
        lines.append(f"Build Number: #{build_number}")
    if build_url:
        lines.append(f"Build URL: {build_url}")
    
    lines.extend([
        "",
        "-" * 60,
        "SUMMARY",
        "-" * 60,
        f"Total Tests: {summary.get('total', 0)}",
        f"Passed: {summary.get('passed', 0)}",
        f"Failed: {summary.get('failed', 0)}",
        f"Errors: {summary.get('errors', 0)}",
        f"Skipped: {summary.get('skipped', 0)}",
        "",
    ])
    
    if report.get("failures"):
        lines.extend([
            "-" * 60,
            "FAILURES",
            "-" * 60,
        ])
        for failure in report["failures"]:
            lines.extend([
                "",
                f"Test: {failure['test_name']}",
                f"Class: {failure['test_class']}",
                f"Method: {failure['test_method']}",
                f"Error: {failure['error_message']}",
                "",
                "Stack Trace:",
                failure['stack_trace'],
            ])
    
    if report.get("errors"):
        lines.extend([
            "-" * 60,
            "ERRORS",
            "-" * 60,
        ])
        for error in report["errors"]:
            lines.extend([
                "",
                f"Test: {error['test_name']}",
                f"Class: {error['test_class']}",
                f"Method: {error['test_method']}",
                f"Error Type: {error['error_type']}",
                f"Error: {error['error_message']}",
                "",
                "Stack Trace:",
                error['stack_trace'],
            ])
    
    lines.extend([
        "",
        "=" * 60,
        "End of Report",
        "=" * 60,
    ])
    
    return "\n".join(lines)


def send_email(report, config):
    """
    Send email notification
    
    Args:
        report: Test report dictionary
        config: Email configuration dictionary containing:
            - smtp_server: SMTP server address
            - smtp_port: SMTP server port
            - smtp_user: SMTP username (optional)
            - smtp_password: SMTP password (optional)
            - sender: Sender email address
            - recipients: List of recipient email addresses
            - job_name: Jenkins job name (optional)
            - build_number: Jenkins build number (optional)
            - build_url: Jenkins build URL (optional)
            - use_tls: Whether to use TLS (default: True)
    """
    # Create message
    msg = MIMEMultipart('alternative')
    
    # Set subject based on test status
    if report.get("all_passed"):
        subject = "Tests Passed"
    else:
        summary = report.get("summary", {})
        failed_count = summary.get("failed", 0) + summary.get("errors", 0)
        subject = f"Tests Failed ({failed_count} failures)"
    
    if config.get("job_name"):
        subject = f"[{config['job_name']}] {subject}"
    
    msg['Subject'] = subject
    msg['From'] = config['sender']
    msg['To'] = ", ".join(config['recipients'])
    
    # Create email bodies
    plain_text = create_plain_text_body(
        report,
        config.get('job_name', ''),
        config.get('build_number', ''),
        config.get('build_url', '')
    )
    
    html_body = create_email_body(
        report,
        config.get('job_name', ''),
        config.get('build_number', ''),
        config.get('build_url', '')
    )
    
    # Attach both plain text and HTML versions
    msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # Send the email
    try:
        if config.get('use_tls', True):
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
        else:
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        
        if config.get('smtp_user') and config.get('smtp_password'):
            server.login(config['smtp_user'], config['smtp_password'])
        
        server.sendmail(
            config['sender'],
            config['recipients'],
            msg.as_string()
        )
        server.quit()
        print(f"Email sent successfully to: {', '.join(config['recipients'])}")
        return True
        
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Send test failure notification email')
    
    # Report file
    parser.add_argument('--report', default='test_report.json', help='Path to test report JSON file')
    
    # SMTP configuration
    parser.add_argument('--smtp-server', default=os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
                        help='SMTP server address')
    parser.add_argument('--smtp-port', type=int, default=int(os.environ.get('SMTP_PORT', '587')),
                        help='SMTP server port')
    parser.add_argument('--smtp-user', default=os.environ.get('SMTP_USER', ''),
                        help='SMTP username')
    parser.add_argument('--smtp-password', default=os.environ.get('SMTP_PASSWORD', ''),
                        help='SMTP password')
    parser.add_argument('--no-tls', action='store_true', help='Disable TLS')
    
    # Email addresses
    parser.add_argument('--sender', default=os.environ.get('EMAIL_SENDER', ''),
                        help='Sender email address')
    parser.add_argument('--recipients', nargs='+', 
                        default=os.environ.get('EMAIL_RECIPIENTS', '').split(','),
                        help='Recipient email addresses')
    
    # Jenkins info
    parser.add_argument('--job-name', default=os.environ.get('JOB_NAME', ''),
                        help='Jenkins job name')
    parser.add_argument('--build-number', default=os.environ.get('BUILD_NUMBER', ''),
                        help='Jenkins build number')
    parser.add_argument('--build-url', default=os.environ.get('BUILD_URL', ''),
                        help='Jenkins build URL')
    
    # Options
    parser.add_argument('--always-send', action='store_true',
                        help='Send email even if all tests pass')
    
    args = parser.parse_args()
    
    # Load report
    try:
        report = load_test_report(args.report)
    except Exception as e:
        print(f"Failed to load test report: {str(e)}")
        return 1
    
    # Check if we should send email
    if report.get("all_passed") and not args.always_send:
        print("All tests passed. No email notification sent.")
        return 0
    
    # Validate required fields
    if not args.sender or not args.recipients or not args.recipients[0]:
        print("Error: --sender and --recipients are required")
        print("You can also set EMAIL_SENDER and EMAIL_RECIPIENTS environment variables")
        return 1
    
    # Prepare config
    config = {
        'smtp_server': args.smtp_server,
        'smtp_port': args.smtp_port,
        'smtp_user': args.smtp_user,
        'smtp_password': args.smtp_password,
        'use_tls': not args.no_tls,
        'sender': args.sender,
        'recipients': [r.strip() for r in args.recipients if r.strip()],
        'job_name': args.job_name,
        'build_number': args.build_number,
        'build_url': args.build_url,
    }
    
    # Send email
    success = send_email(report, config)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
