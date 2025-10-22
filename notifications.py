import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import requests
import json

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Email configuration - Use environment variables or fallback to hardcoded values
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "doshikrahul@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "gnil ytab humm jauh")  # App password
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "rahulrepaka02@gmail.com")
SENDER_NAME = "ComplianceBot"

# Slack configuration
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")  # Get from https://api.slack.com/messaging/webhooks
SLACK_ENABLED = os.getenv("SLACK_ENABLED", "false").lower() == "true"

def send_slack_notification(message, title=None, color="warning"):
    """
    Send notification to Slack via webhook.
    
    Args:
        message (str): Message body
        title (str): Optional title for the message
        color (str): Color of the message attachment (good, warning, danger)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not SLACK_ENABLED or not SLACK_WEBHOOK_URL:
        logger.debug("Slack notifications disabled or webhook URL not configured")
        return False
    
    try:
        # Format message for Slack
        payload = {
            "attachments": [{
                "color": color,
                "title": title if title else "Contract Compliance Checker Alert",
                "text": message,
                "footer": "ComplianceBot",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("✅ Slack notification sent successfully")
            return True
        else:
            logger.error(f"❌ Slack notification failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending Slack notification: {e}")
        return False

def send_notification(subject, notification):
    """
    Send email notification for errors and updates.
    Also sends to Slack if enabled.
    
    Args:
        subject (str): Email subject line
        notification (str): Email body content
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    email_sent = False
    slack_sent = False
    
    # Send email
    try:
        # Create message
        msg = MIMEText(f"{notification}")
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = RECEIVER_EMAIL
        
        # Connect to Gmail SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Start TLS encryption
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Email sent successfully: {subject}")
        email_sent = True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ Email authentication failed: {e}")
        logger.error("Please check your Gmail App Password")
    except Exception as e:
        logger.error(f"❌ Error occurred while sending email: {e}")
    
    # Send Slack notification
    if SLACK_ENABLED:
        slack_sent = send_slack_notification(notification, title=subject)
    
    return email_sent or slack_sent

def send_rate_limit_alert(keys_status, retry_count, wait_time=None):
    """
    Send notification when all API keys hit rate limits.
    Sends both email and Slack notifications.
    
    Args:
        keys_status (dict): Status of all API keys
        retry_count (int): Number of retries attempted
        wait_time (float): Wait time in seconds until next key is available
    
    Returns:
        bool: True if any notification sent successfully, False otherwise
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    subject = "⚠️ API Rate Limit Alert - All Keys Exhausted"
    
    # Email body (detailed)
    email_body = f"""
{'='*70}
⚠️  GROQ API RATE LIMIT ALERT
{'='*70}

Time: {timestamp}
Status: ALL API KEYS RATE LIMITED
Retries Attempted: {retry_count}

{'='*70}
KEY STATUS:
{'='*70}

"""
    
    for key_num, status in keys_status.items():
        email_body += f"Key {key_num}: {status}\n"
    
    email_body += f"\n{'='*70}\n"
    
    if wait_time:
        minutes = int(wait_time // 60)
        seconds = int(wait_time % 60)
        email_body += f"\nNext available key in: {minutes}m {seconds}s\n"
    
    email_body += f"""
{'='*70}
RECOMMENDED ACTIONS:
{'='*70}

1. Wait for cooldown period to expire
2. Consider upgrading to Dev Tier for higher limits
3. Optimize document processing to reduce token usage
4. Add more API keys to your configuration

Groq Console: https://console.groq.com/settings/billing

This is an automated alert from the Contract Compliance Checker.
"""
    
    # Slack message (concise)
    slack_message = f"🚨 *ALL API KEYS RATE LIMITED*\n\n"
    slack_message += f"*Time:* {timestamp}\n"
    slack_message += f"*Retries:* {retry_count}\n\n"
    
    if wait_time:
        minutes = int(wait_time // 60)
        seconds = int(wait_time % 60)
        slack_message += f"*Next available:* {minutes}m {seconds}s\n\n"
    
    slack_message += "*Key Status:*\n"
    for key_num, status in keys_status.items():
        slack_message += f"• Key {key_num}: {status}\n"
    
    slack_message += f"\n💡 Consider upgrading to Dev Tier at <https://console.groq.com/settings/billing|Groq Console>"
    
    # Send both notifications
    email_sent = send_notification(subject, email_body)
    slack_sent = False
    
    if SLACK_ENABLED:
        slack_sent = send_slack_notification(slack_message, title="⚠️ API Rate Limit Alert", color="danger")
    
    return email_sent or slack_sent

def send_compliance_result(result, document_name, agreement_type):
    """
    Send compliance analysis result via email and Slack.
    
    Args:
        result: The compliance analysis result (string or dict)
        document_name (str): Name of the analyzed document
        agreement_type (str): Type of agreement detected
    
    Returns:
        bool: True if any notification sent successfully, False otherwise
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"✅ Compliance Analysis Complete: {document_name}"
    
    # Email body (detailed)
    email_body = f"""
Contract Compliance Analysis Report
{'='*70}

Document: {document_name}
Agreement Type: {agreement_type}
Timestamp: {timestamp}

{'='*70}
ANALYSIS RESULTS:
{'='*70}

{result}

{'='*70}

This is an automated notification from the Contract Compliance Checker.
"""
    
    # Slack message (concise)
    result_preview = str(result)[:500] + "..." if len(str(result)) > 500 else str(result)
    slack_message = f"✅ *Compliance Analysis Complete*\n\n"
    slack_message += f"*Document:* {document_name}\n"
    slack_message += f"*Type:* {agreement_type}\n"
    slack_message += f"*Time:* {timestamp}\n\n"
    slack_message += f"*Results Preview:*\n```{result_preview}```\n\n"
    slack_message += "_Check your email for full analysis results_"
    
    email_sent = False
    slack_sent = False
    
    # Send email
    try:
        msg = MIMEText(email_body)
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = RECEIVER_EMAIL
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Compliance result email sent successfully")
        email_sent = True
        
    except Exception as e:
        logger.error(f"❌ Error sending compliance result email: {e}")
    
    # Send Slack notification
    if SLACK_ENABLED:
        slack_sent = send_slack_notification(slack_message, title="✅ Compliance Analysis Complete", color="good")
    
    return email_sent or slack_sent


# Test function (optional - only runs when executed directly)
if __name__ == "__main__":
    test_subject = "Test Notification"
    test_message = "This is a test notification from the Contract Compliance Checker."
    print("Testing email notification system...")
    if send_notification(test_subject, test_message):
        print("✅ Test email sent successfully!")
    else:
        print("❌ Test email failed!")
