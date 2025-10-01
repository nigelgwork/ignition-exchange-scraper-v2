"""
Notification system for email, Discord, and Microsoft Teams
"""
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, List
from pathlib import Path


def send_email_notification(config: Dict, subject: str, body: str, html_body: str = None, attachment_path: Path = None) -> bool:
    """
    Send email notification with optional file attachment

    Args:
        config: Email configuration dict with keys: smtp_server, smtp_port, username, password, from_email, to_emails
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
        attachment_path: Optional path to file to attach

    Returns:
        True if successful, False otherwise
    """
    try:
        if not config.get('enabled'):
            return False

        msg = MIMEMultipart('mixed')
        msg['From'] = config.get('from_email', config.get('username'))
        msg['To'] = ', '.join(config.get('to_emails', []))
        msg['Subject'] = subject

        # Create alternative part for text/html
        msg_alternative = MIMEMultipart('alternative')
        msg_alternative.attach(MIMEText(body, 'plain'))
        if html_body:
            msg_alternative.attach(MIMEText(html_body, 'html'))
        msg.attach(msg_alternative)

        # Attach file if provided
        if attachment_path and attachment_path.exists():
            with open(attachment_path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                attachment.add_header('Content-Disposition', 'attachment', filename=attachment_path.name)
                msg.attach(attachment)

        # Connect and send
        with smtplib.SMTP(config.get('smtp_server'), config.get('smtp_port', 587)) as server:
            server.starttls()
            server.login(config.get('username'), config.get('password'))
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Email notification failed: {e}")
        return False


def send_discord_notification(config: Dict, message: str, embeds: List[Dict] = None, file_path: Path = None) -> bool:
    """
    Send Discord webhook notification with optional file attachment

    Args:
        config: Discord configuration with 'webhook_url'
        message: Message content
        embeds: Optional list of embed dicts
        file_path: Optional path to file to attach

    Returns:
        True if successful, False otherwise
    """
    try:
        if not config.get('enabled'):
            return False

        webhook_url = config.get('webhook_url')
        if not webhook_url:
            return False

        # Prepare payload
        payload = {'content': message}
        if embeds:
            payload['embeds'] = embeds

        # If file is provided, send as multipart/form-data
        if file_path and file_path.exists():
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                data = {'payload_json': json.dumps(payload)}
                response = requests.post(webhook_url, data=data, files=files, timeout=30)
        else:
            response = requests.post(webhook_url, json=payload, timeout=10)

        return response.status_code == 204 or response.status_code == 200
    except Exception as e:
        print(f"Discord notification failed: {e}")
        return False


def send_teams_notification(config: Dict, title: str, text: str, facts: List[Dict] = None, file_path: Path = None) -> bool:
    """
    Send Microsoft Teams webhook notification

    Note: Teams webhooks do not support direct file attachments. The file_path parameter is included
    for API consistency but the filename will only be mentioned in the message.

    Args:
        config: Teams configuration with 'webhook_url'
        title: Card title
        text: Card text
        facts: Optional list of fact dicts with 'name' and 'value' keys
        file_path: Optional path to file (filename will be mentioned in message)

    Returns:
        True if successful, False otherwise
    """
    try:
        if not config.get('enabled'):
            return False

        webhook_url = config.get('webhook_url')
        if not webhook_url:
            return False

        # Add note about file if provided
        if file_path and file_path.exists():
            text = f"{text}\n\n**Report file available:** {file_path.name}"

        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": title,
            "themeColor": "0078D4",
            "title": title,
            "text": text
        }

        if facts:
            card["sections"] = [{
                "facts": facts
            }]

        response = requests.post(webhook_url, json=card, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Teams notification failed: {e}")
        return False


def notify_scrape_complete(config: Dict, stats: Dict, excel_file_path: Path) -> Dict[str, bool]:
    """
    Send notifications about completed scrape to all enabled channels

    Args:
        config: Full notification configuration
        stats: Statistics dict from comparison
        excel_file_path: Path to generated Excel file

    Returns:
        Dict with success status for each channel
    """
    results = {
        'email': False,
        'discord': False,
        'teams': False
    }

    excel_filename = excel_file_path.name

    # Prepare message content
    subject = f"Exchange Scraper Complete - {stats.get('total_updated', 0)} Updates Found"

    plain_body = f"""
Exchange Scraper Job Complete

Total Resources: {stats.get('total_current', 0)}
New Resources: {stats.get('new_count', 0)}
Updated Resources: {stats.get('modified_count', 0)}
Total Changes: {stats.get('total_updated', 0)}

Report File: {excel_filename}

This is an automated message from the Ignition Exchange Scraper.
    """.strip()

    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2 style="color: #2563eb;">Exchange Scraper Job Complete</h2>
    <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
        <tr><td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Total Resources:</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{stats.get('total_current', 0)}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>New Resources:</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{stats.get('new_count', 0)}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Updated Resources:</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{stats.get('modified_count', 0)}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Total Changes:</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-weight: bold; color: #2563eb;">{stats.get('total_updated', 0)}</td></tr>
    </table>
    <p style="margin-top: 20px; color: #6b7280;">Report File: <strong>{excel_filename}</strong></p>
    <p style="margin-top: 20px; font-size: 12px; color: #9ca3af;">This is an automated message from the Ignition Exchange Scraper.</p>
</body>
</html>
    """.strip()

    # Send Email with attachment
    if config.get('email', {}).get('enabled'):
        results['email'] = send_email_notification(
            config['email'],
            subject,
            plain_body,
            html_body,
            excel_file_path
        )

    # Send Discord with file
    if config.get('discord', {}).get('enabled'):
        discord_message = f"**{subject}**"
        discord_embeds = [{
            "title": "Scrape Statistics",
            "color": 0x2563eb,  # Blue color
            "fields": [
                {"name": "Total Resources", "value": str(stats.get('total_current', 0)), "inline": True},
                {"name": "New Resources", "value": str(stats.get('new_count', 0)), "inline": True},
                {"name": "Updated Resources", "value": str(stats.get('modified_count', 0)), "inline": True},
                {"name": "Total Changes", "value": str(stats.get('total_updated', 0)), "inline": True}
            ]
        }]
        results['discord'] = send_discord_notification(
            config['discord'],
            discord_message,
            discord_embeds,
            excel_file_path
        )

    # Send Teams with file reference
    if config.get('teams', {}).get('enabled'):
        teams_facts = [
            {"name": "Total Resources", "value": str(stats.get('total_current', 0))},
            {"name": "New Resources", "value": str(stats.get('new_count', 0))},
            {"name": "Updated Resources", "value": str(stats.get('modified_count', 0))},
            {"name": "Total Changes", "value": str(stats.get('total_updated', 0))}
        ]
        results['teams'] = send_teams_notification(
            config['teams'],
            subject,
            "The Exchange scraper has completed successfully.",
            teams_facts,
            excel_file_path
        )

    return results
