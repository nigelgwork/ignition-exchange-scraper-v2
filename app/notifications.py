"""
Notification system for Discord, Microsoft Teams, and ntfy
"""
import json
import requests
from typing import Dict, List
from pathlib import Path


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


def send_ntfy_notification(config: Dict, title: str, message: str, priority: int = 3, tags: List[str] = None, attach_url: str = None) -> bool:
    """
    Send ntfy notification

    Args:
        config: ntfy configuration with 'server_url' and 'topic'
        title: Notification title
        message: Notification message
        priority: Priority level (1=min, 3=default, 5=max)
        tags: Optional list of tags (e.g., ['warning', 'check'])
        attach_url: Optional URL to attach (e.g., link to download file)

    Returns:
        True if successful, False otherwise
    """
    try:
        if not config.get('enabled'):
            print(f"ntfy notification skipped: not enabled")
            return False

        server_url = config.get('server_url', 'https://ntfy.sh')
        topic = config.get('topic')

        if not topic:
            print(f"ntfy notification failed: no topic configured")
            return False

        # Construct the full URL
        url = f"{server_url.rstrip('/')}/{topic}"

        # Prepare headers
        headers = {
            'Title': title,
            'Priority': str(priority)
        }

        if tags:
            headers['Tags'] = ','.join(tags)

        if attach_url:
            headers['Attach'] = attach_url

        print(f"Sending ntfy notification to {url}")
        print(f"Headers: {headers}")

        # Send the notification
        response = requests.post(url, data=message.encode('utf-8'), headers=headers, timeout=10)
        print(f"ntfy response status: {response.status_code}")
        print(f"ntfy response text: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"ntfy notification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def notify_scrape_complete(config: Dict, stats: Dict, excel_file_path: Path, updated_resources: List[Dict] = None) -> Dict[str, bool]:
    """
    Send notifications about completed scrape to all enabled channels

    Args:
        config: Full notification configuration
        stats: Statistics dict from comparison
        excel_file_path: Path to generated Excel file
        updated_resources: Optional list of updated resources to include in notifications

    Returns:
        Dict with success status for each channel
    """
    results = {
        'discord': False,
        'teams': False,
        'ntfy': False
    }

    excel_filename = excel_file_path.name
    total_changes = stats.get('total_updated', 0)

    # Prepare message content
    if total_changes == 0:
        subject = "Exchange Scraper Complete - No Changes Detected"
        changes_summary = "No changes were detected in this scrape."
    else:
        subject = f"Exchange Scraper Complete - {total_changes} Update{'' if total_changes == 1 else 's'} Found"

        # Format changes for plain text
        changes_list = []
        if updated_resources:
            for i, resource in enumerate(updated_resources[:10], 1):  # Limit to 10 for brevity
                title = resource.get('title', 'Unknown')
                version = resource.get('version', 'N/A')
                changes_list.append(f"{i}. {title} (v{version})")

            changes_summary = "Changes:\n" + "\n".join(changes_list)
            if len(updated_resources) > 10:
                changes_summary += f"\n... and {len(updated_resources) - 10} more"
        else:
            changes_summary = f"{total_changes} resources were updated."

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

    # Send ntfy notification
    if config.get('ntfy', {}).get('enabled'):
        ntfy_message = f"""Exchange Scraper Complete

Total Resources: {stats.get('total_current', 0)}
New: {stats.get('new_count', 0)} | Updated: {stats.get('modified_count', 0)}
Total Changes: {total_changes}

{changes_summary}"""

        tags = ['white_check_mark'] if total_changes == 0 else ['bell']
        priority = 3 if total_changes == 0 else 4

        results['ntfy'] = send_ntfy_notification(
            config['ntfy'],
            subject,
            ntfy_message,
            priority=priority,
            tags=tags
        )

    return results
