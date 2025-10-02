# Ignition Exchange Scraper v2

Automated web scraper for tracking and monitoring resources on the Ignition Exchange platform. Features scheduled scraping, change detection, multi-platform notifications, and a modern web dashboard.

## Features

- 🔄 **Automated Scheduling**: Configure scraping intervals (default: weekly)
- 📊 **Change Detection**: Automatically compares new results with previous scrapes
- 📢 **Multi-Platform Notifications**: Discord, Microsoft Teams, and ntfy support
- 🗂️ **Excel Reports**: Detailed reports with clickable URLs across multiple sheets
- 🌐 **Web Dashboard**: Modern UI for monitoring, configuration, and manual control
- 🎨 **Dark Mode**: Toggle between light and dark themes
- 🐳 **Fully Containerized**: Single command deployment with Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Port 9089 available for the web dashboard

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ignition-exchange-scraper-v2
   ```

2. **Start the application**
   ```bash
   docker compose up -d
   ```

3. **Access the dashboard**
   - Open your browser to: http://localhost:9089

## Usage

### Web Dashboard

The dashboard provides real-time monitoring and control:

- **Status Panel**: View current scraping progress, elapsed time, and estimates
- **Quick Actions**: Run scraper manually, pause, or stop operations
- **Schedule Configuration**: Set scraping intervals (in days)
- **Live Activity Log**: Real-time log stream of scraper activity
- **Recent Jobs**: History of completed scraping jobs
- **View Data**: Download generated Excel reports
- **View Changes**: See what's new or updated in the latest scrape

### Notifications

Configure notifications to receive alerts when scraping completes:

1. Click the **Notifications** button in the dashboard
2. Enable and configure your preferred platform(s):

#### Discord
- **Setup**: Create a webhook in your Discord server
  - Server Settings → Integrations → Webhooks → New Webhook
- **Configuration**: Paste the webhook URL
- **Features**: Includes embedded statistics and Excel file attachment

#### Microsoft Teams
- **Setup**: Create an incoming webhook in your Teams channel
  - Channel → ⋯ → Connectors → Incoming Webhook
- **Configuration**: Paste the webhook URL
- **Features**: Adaptive card with statistics (file reference only)

#### ntfy
- **Setup**: Choose a unique topic name
- **Configuration**:
  - Server URL: `https://ntfy.sh` (or your own server)
  - Topic: Your unique topic name
- **Features**: Simple push notifications with priority levels
- **Mobile**: Install ntfy app and subscribe to your topic

3. Click **Save** to store your configuration
4. Use individual **Test** buttons to verify each platform

### Manual Control

- **Run Now**: Start an immediate scrape (regardless of schedule)
- **Pause**: Temporarily pause an in-progress scrape
- **Stop**: Halt the current scrape operation
- **Schedule**: Configure interval between automatic scrapes

## Data Persistence

All data is stored in the `./data` directory (Docker volume):

- `config.json`: Schedule and notification settings
- `state.json`: Current scraper state and progress
- `job_history.json`: Historical job records
- `past_results_cache.json`: Previous scrape results for comparison
- `activity.log`: Application activity logs
- `output/`: Generated Excel report files

## Excel Report Format

Each report contains three sheets:

1. **Updated Results**: Only new or modified resources since last scrape
2. **Current Results**: Complete list of all resources from current scrape
3. **Past Results**: Complete list from the previous scrape

All URLs are clickable links for easy navigation.

## Configuration Files

### config.json
```json
{
  "interval_days": 7,
  "enabled": true,
  "notifications": {
    "discord": {
      "enabled": false,
      "webhook_url": ""
    },
    "teams": {
      "enabled": false,
      "webhook_url": ""
    },
    "ntfy": {
      "enabled": false,
      "server_url": "https://ntfy.sh",
      "topic": ""
    }
  }
}
```

## Security Considerations

### For Local/Development Use
- The application runs on HTTP by default
- Webhook URLs contain sensitive tokens - protect your `config.json`
- Keep the `./data` directory private (contains configuration and logs)

### For Production Use
- Deploy behind a reverse proxy with HTTPS (nginx, Traefik, Caddy)
- Use environment variables for sensitive configuration
- Implement authentication if exposing to the internet
- Regularly review notification webhook permissions
- Consider using a private ntfy server for sensitive notifications

### Security Review Findings

**Potential Security Concerns:**
1. **Webhook SSRF**: The notification system makes HTTP requests to user-provided URLs
   - **Mitigation**: Only configured administrators should access the dashboard
   - **Recommendation**: Run in isolated network or use firewall rules

2. **File Operations**: File download/delete endpoints validate file extensions and prevent path traversal
   - All file operations are restricted to `.xlsx` files only
   - Path traversal is blocked by checking for `/` and `\` characters

3. **No Authentication**: The web dashboard has no built-in authentication
   - **Mitigation**: Deploy behind authenticated reverse proxy for production
   - **Recommendation**: Use tools like Authelia, OAuth2 Proxy, or Cloudflare Access

## Troubleshooting

### Containers won't start
```bash
# Check logs
docker compose logs

# Rebuild containers
docker compose down
docker compose up -d --build
```

### Scraper not running
- Check the Live Activity Log in the dashboard
- Verify the schedule interval is set correctly
- Ensure the scheduler container is running: `docker compose ps`

### Notifications not sending
- Use the **Test** buttons to verify configuration
- Check webhook URLs are correct and active
- Review the Activity Log for error messages
- Verify network connectivity from container

### Excel files not generating
- Check if scraper completed successfully in Recent Jobs
- Look for errors in the Activity Log
- Verify `data/output/` directory has write permissions

## Development

### Project Structure
```
/
├── exchange_scraper_fixed.py   # Core scraping logic
├── app/
│   ├── webserver.py            # Flask API server
│   ├── scheduler.py            # Background job scheduler
│   ├── notifications.py        # Multi-platform notifications
│   ├── comparison.py           # Change detection logic
│   ├── excel_generator.py     # Excel report generation
│   └── static/
│       └── index.html          # Web dashboard UI
├── data/                       # Persistent data (Docker volume)
├── Dockerfile                  # Container build instructions
├── docker-compose.yml          # Service orchestration
└── requirements.txt            # Python dependencies
```

### Running Tests
The application includes a test report generator:

```bash
docker compose exec scheduler python app/generate_test_report.py
```

## License

This project is provided as-is for monitoring the Inductive Automation Ignition Exchange.

## Contributing

Contributions welcome! Please ensure:
- Code follows existing style
- Security considerations are documented
- Testing is performed before submitting PRs
