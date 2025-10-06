# Claude.md - Ignition Exchange Scraper v2

This file contains build commands, code style conventions, and key architectural decisions for the Ignition Exchange Scraper v2 project.

## Project Overview

Automated web scraper for tracking and monitoring resources on the Ignition Exchange platform. Features scheduled scraping, change detection, multi-platform notifications (Discord, Teams, ntfy), and a modern web dashboard. Fully containerized for easy deployment.

## Build Commands

### Development & Deployment

```bash
# Build and start all services
docker compose up -d

# Rebuild containers after code changes
docker compose up -d --build

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f web
docker compose logs -f scheduler

# Stop all services
docker compose down

# Restart specific service
docker compose restart web
docker compose restart scheduler

# Check service status
docker compose ps
```

### Testing

```bash
# Generate test report (inside container)
docker compose exec scheduler python app/generate_test_report.py

# Run scraper manually (inside container)
docker compose exec scheduler python exchange_scraper_fixed.py
```

### File Operations

```bash
# Access data directory
cd data/

# View activity logs
tail -f data/activity.log

# View configuration
cat data/config.json

# View job history
cat data/job_history.json

# List generated Excel reports
ls -lh data/output/
```

## Architecture

### Container Structure
- **web**: Flask API server and dashboard (port 9089)
- **scheduler**: Background job scheduler and scraper engine

### Data Flow
1. Scheduler runs scraper on configured interval (default: 7 days)
2. Scraper extracts resources using Playwright + BeautifulSoup
3. Comparison engine detects changes vs. previous results
4. Excel generator creates 3-sheet report (Updated/Current/Past)
5. Notifications sent via Discord/Teams/ntfy
6. Results cached for next comparison

### File Structure
```
/
├── exchange_scraper_fixed.py   # Core scraping engine
├── app/
│   ├── webserver.py            # Flask API + dashboard endpoints
│   ├── scheduler.py            # APScheduler + job management
│   ├── notifications.py        # Multi-platform notifications
│   ├── comparison.py           # Change detection logic
│   ├── excel_generator.py     # Excel report generation
│   └── static/index.html       # Web dashboard UI
├── data/                       # Persistent data (Docker volume)
│   ├── config.json            # Settings + notification config
│   ├── state.json             # Scraper state + progress
│   ├── activity.log           # Application logs
│   ├── job_history.json       # Historical job records
│   ├── past_results_cache.json # Previous scrape results
│   └── output/                # Generated Excel reports
├── Dockerfile                 # Container build
├── docker-compose.yml         # Service orchestration
├── requirements.txt           # Python dependencies
└── README.md                  # User documentation
```

## Code Style & Conventions

### Python Style
- **PEP 8 compliant**: Follow standard Python style guide
- **Type hints**: Use typing module for function parameters and returns
- **Docstrings**: Google-style docstrings for all public functions/classes
- **String quotes**: Single quotes preferred, double for docstrings
- **Line length**: 120 characters max (practical limit)
- **Imports**: Standard library → Third-party → Local, alphabetically sorted within groups

### Naming Conventions
- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`
- **File names**: `lowercase_with_underscores.py`

### Key Patterns

#### Logging
```python
# Always use Adelaide timezone for timestamps
from zoneinfo import ZoneInfo
ADELAIDE_TZ = ZoneInfo("Australia/Adelaide")

# Log format
def append_log(message: str, level: str = 'info'):
    log_entry = {
        'timestamp': datetime.now(ADELAIDE_TZ).isoformat(),
        'message': message,
        'level': level
    }
```

#### Progress Callbacks
```python
# Scraper uses progress callbacks for real-time updates
def progress_callback(data: dict):
    if data['type'] == 'log':
        # Handle log messages
    elif data['type'] == 'progress':
        # Update progress indicators
```

#### File Safety
```python
# Always validate file operations
if not filename.endswith('.xlsx') or '/' in filename or '\\' in filename:
    return jsonify({'error': 'Invalid filename'}), 400
```

#### State Management
```python
# Use file-based state for cross-container communication
state = load_state()
state['status'] = 'running'
save_state(state)
```

#### Control Signals
```python
# Signal files for inter-process communication
control_file = DATA_DIR / f'control_{action}.signal'
control_file.touch()
```

### Error Handling
- **Graceful degradation**: Continue operation on non-critical errors
- **User feedback**: Log all errors to activity log
- **Notifications**: Send failure notifications on job errors
- **Retries**: No automatic retries (manual intervention required)

### Date & Time
- **Timezone**: All timestamps use Adelaide timezone (`Australia/Adelaide`)
- **Date format (display)**: `DD/MM/YYYY HH:MM:SS` (Australian format)
- **Date format (filenames)**: `DDMMYY` (e.g., `061025` for October 6, 2025)
- **ISO format**: Used for JSON serialization and API responses

### Excel Reports
- **Filename format**: `Ignition Exchange Resource Results_DDMMYY.xlsx`
- **Sheet order**: Updated Results → Current Results → Past Results
- **Sorting**: By Resource ID (extracted from URL)
- **Headers**: Resource ID | Title | URL | Version | Updated Date | Developer ID | Contributor | Tagline
- **Styling**: Blue header with white text, clickable URLs

### Version Formatting
- **Input**: Raw version numbers like `100030000`
- **Output**: Semantic versioning like `1.3.0`
- **Pattern**: 9-digit → `major.minor.patch`

### API Endpoints

#### Status & Control
- `GET /api/status` - Current scraper status
- `GET /api/config` - Get configuration
- `POST /api/config` - Update configuration
- `POST /api/control/<action>` - Control scraper (run/pause/stop/resume)

#### Data Access
- `GET /api/logs?limit=N` - Recent activity logs
- `POST /api/logs/clear` - Clear activity logs
- `GET /api/history` - Job history
- `GET /api/files` - List Excel reports
- `GET /api/download/<filename>` - Download Excel file
- `DELETE /api/delete/<filename>` - Delete Excel file
- `GET /api/changes` - Latest changes from most recent report

#### Notifications
- `POST /api/test-notification/<channel>` - Test notification (discord/teams/ntfy)

#### Health
- `GET /health` - Health check endpoint

### Configuration Schema

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

## Key Technical Decisions

### Why Playwright?
- **Dynamic content**: Exchange site uses JavaScript-heavy React components
- **Load more**: Requires clicking buttons to load all resources
- **Network inspection**: Captures API responses for data extraction
- **Modal handling**: Automated popup dismissal

### Why APScheduler?
- **Python native**: No external dependencies (cron, etc.)
- **Dynamic updates**: Can reschedule jobs without restart
- **Timezone aware**: Built-in support for timezones
- **Misfire grace**: Runs missed jobs regardless of latency

### Why File-Based State?
- **Cross-container**: Shared volume between web and scheduler containers
- **Persistence**: Survives container restarts
- **Simplicity**: No database overhead for small-scale application
- **Signal files**: Elegant inter-process communication

### Why Three Excel Sheets?
- **Updated**: Quick view of changes (primary use case)
- **Current**: Complete snapshot for analysis
- **Past**: Historical reference for comparison

### Why Adelaide Timezone?
- **User preference**: User is based in Adelaide
- **Consistency**: All timestamps use same timezone
- **Job scheduling**: Predictable execution times

### Why ntfy + Discord + Teams?
- **User preference**: User requested ntfy support
- **Multi-platform**: Different notification needs (mobile vs. desktop)
- **Flexibility**: Enable/disable independently

### Security Considerations
- **Local deployment**: Default configuration for local/trusted network
- **No authentication**: Designed for single-user local use
- **File validation**: Path traversal prevention on downloads/deletes
- **Webhook SSRF**: Acknowledged risk - run in isolated network
- **Production notes**: Deploy behind authenticated reverse proxy with HTTPS

## Git Workflow

### Protected Files
The following files are preserved across git operations (via .gitignore):
- `data/output/*.xlsx` - Generated Excel reports
- `data/*.json` - Configuration and state files
- `data/*.log` - Activity logs

### Git Commands
```bash
# View status
git status

# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add Adelaide timezone support"

# View history
git log --oneline -10

# View specific file changes
git diff app/scheduler.py
```

### Commit Message Format
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **refactor**: Code restructuring
- **style**: Formatting changes
- **test**: Test additions

## Development Notes

### Adding New Notification Channels
1. Create send function in `app/notifications.py`
2. Add channel config to config schema
3. Update `notify_scrape_complete()` to call new function
4. Add test endpoint to `app/webserver.py`
5. Update dashboard UI with new channel form

### Adding New Scraper Fields
1. Add selectors to `exchange_scraper_fixed.py`
2. Update extraction logic in `extract_resource_details()`
3. Add field to headers in `app/excel_generator.py`
4. Update comparison logic if needed

### Debugging Scraper Issues
1. Set `HEADLESS = False` in `exchange_scraper_fixed.py`
2. Run scraper manually: `docker compose exec scheduler python exchange_scraper_fixed.py`
3. Check debug samples in `debug_samples/` directory
4. Review activity log for errors

### Performance Tuning
- **Load attempts**: `LOAD_MORE_ATTEMPTS = 100` (increase for more resources)
- **Timeouts**: `NAV_TIMEOUT = 60000` (navigation) / `SELECTOR_TIMEOUT = 15000` (elements)
- **Sleep delays**: Balance between speed and reliability
- **Consecutive no-change**: `max_no_change = 3` (stop after 3 failed load attempts)

## Testing Strategy

### Manual Testing
1. Run scraper via dashboard "Run Now" button
2. Verify progress updates in real-time
3. Check Excel report generation
4. Test notifications using "Test" buttons
5. Verify change detection with modified data

### Integration Testing
1. Deploy with Docker Compose
2. Test full workflow: schedule → scrape → compare → notify
3. Test pause/stop/resume controls
4. Test file download/delete operations
5. Verify state persistence across restarts

## Maintenance

### Regular Tasks
- **Log rotation**: Activity logs grow over time (clear via dashboard)
- **Job history**: Automatically limited to 50 most recent jobs
- **Excel reports**: Manually delete old reports if disk space is concern
- **Dependency updates**: Check for security updates monthly

### Troubleshooting Checklist
1. Check container status: `docker compose ps`
2. View logs: `docker compose logs -f`
3. Verify data directory permissions
4. Check disk space in data volume
5. Test network connectivity from containers
6. Verify webhook URLs are accessible
7. Check for Playwright browser updates

## Future Enhancement Ideas
- Database backend for better querying
- Email notification support
- Webhook for custom integrations
- Resource filtering/tagging
- Diff view between versions
- Mobile app integration
- Custom scraping intervals per resource
- Backup/restore functionality
- Multi-user support with authentication
- REST API for external integrations

## Contact & Support
- Project repository: TBD (add your repo URL)
- Issues: Report via GitHub issues
- Documentation: README.md and this file

---

**Last Updated**: October 2025
**Project Version**: 2.0
