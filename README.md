# Ignition Exchange Resource Change Tracker

A containerized application that scrapes the Inductive Automation Ignition Exchange website daily, tracks resource changes (new or updated projects), generates comparison reports in Excel format, and provides a web dashboard for monitoring and control.

## Features

- **Automated Daily Scraping**: Scrapes the Ignition Exchange website on a configurable schedule
- **Change Detection**: Identifies new and updated resources by comparing versions and update dates
- **Excel Reports**: Generates comprehensive reports with 3 sheets:
  - Updated Results (new and modified resources)
  - Current Results (all resources from latest scrape)
  - Past Results (all resources from previous scrape)
- **Web Dashboard**: Real-time monitoring with:
  - Current scraper status and progress
  - Live activity log
  - Schedule configuration
  - Manual controls (Run, Pause, Stop)
  - Job history
  - Report downloads
- **Fully Containerized**: Runs via `docker compose up` - no additional setup required

## Quick Start

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1. **Clone or navigate to the project directory**:
   ```bash
   cd ignition-exchange-scraper-v2
   ```

2. **Start the application**:
   ```bash
   docker compose up -d
   ```

3. **Access the dashboard**:
   Open your browser and navigate to:
   ```
   http://localhost:9089
   ```

4. **Stop the application**:
   ```bash
   docker compose down
   ```

## Project Structure

```
/
├── exchange_scraper_fixed.py      # Core scraper logic with Playwright
├── app/
│   ├── webserver.py               # Flask web server and API
│   ├── scheduler.py               # APScheduler worker service
│   ├── comparison.py              # Resource comparison logic
│   ├── excel_generator.py         # Excel report generation
│   └── static/
│       └── index.html             # Web dashboard (HTML/CSS/JS)
├── data/                          # Persistent data (Docker volume)
│   ├── past_results_cache.json    # Previous scrape results
│   └── output/                    # Generated Excel reports
├── Dockerfile                     # Container image definition
├── docker-compose.yml             # Multi-service orchestration
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Architecture

The application consists of two Docker services:

### 1. Web Service
- **Port**: 9089
- **Purpose**: Serves the web dashboard and provides REST API
- **Endpoints**:
  - `GET /` - Web dashboard
  - `GET /api/status` - Current scraper status
  - `GET /api/config` - Configuration
  - `POST /api/config` - Update configuration
  - `POST /api/control/<action>` - Control scraper (run/pause/stop/resume)
  - `GET /api/logs` - Activity logs
  - `POST /api/logs/clear` - Clear logs
  - `GET /api/history` - Job history
  - `GET /api/files` - List available reports
  - `GET /api/download/<filename>` - Download report

### 2. Scheduler Service
- **Purpose**: Runs scraper jobs on schedule
- **Features**:
  - Configurable interval (default: 7 days)
  - Monitors control signals from web service
  - Updates state for real-time dashboard updates
  - Performs comparison and generates Excel reports
  - Maintains job history

### Data Persistence

All data is stored in the `./data` directory, which is mounted as a Docker volume:
- `past_results_cache.json` - Complete dataset from last successful scrape
- `state.json` - Current scraper state (progress, status, etc.)
- `config.json` - User configuration (schedule interval)
- `activity.log` - Activity logs
- `job_history.json` - Historical job records
- `output/*.xlsx` - Generated Excel reports

## Usage Guide

### Dashboard Overview

The web dashboard features a modern interface with:
- **Pastel color scheme**: Easy-on-the-eyes button colors throughout
- **Dark mode**: Toggle between light and dark themes using the moon icon switch in the header (preference saved locally)

#### Current Status
- Real-time scraper status (Idle, Running, Paused, Stopped, Done, Failed)
- Progress bar with item count and percentage
- Current item being scraped
- Elapsed and estimated remaining time

#### Schedule Configuration
- Set scraping interval in days
- View next scheduled run time
- Save changes to apply immediately

#### Quick Actions
- **Run Now**: Trigger immediate scrape
- **Pause**: Temporarily pause running scrape
- **Stop**: Stop scrape completely
- **View Data**: Browse and download Excel reports

#### Live Activity Log
- Real-time log entries with timestamps
- Color-coded by severity (info, warning, error)
- Auto-scrolls to latest entries
- Clearable

#### Recent Jobs
- Historical job records
- Date, duration, status, count, and errors
- Shows last 10 jobs

### Excel Reports

Reports are named: `Ignition Exchange Resource Results_YYMMDD.xlsx`

Each report contains 3 sheets:

1. **Updated Results**: Only new or modified resources since last scrape
2. **Current Results**: All resources from current scrape
3. **Past Results**: All resources from previous scrape

Columns in each sheet:
- Title
- URL
- Version
- Updated Date
- Developer ID
- Contributor
- Tagline

### Comparison Logic

A resource is considered "updated" if:
- **New**: The title didn't exist in previous scrape
- **Modified**: The title exists but version or update date has changed

## Configuration

### Changing Scrape Interval

**Via Dashboard**:
1. Enter desired days in "Run Every" field
2. Click "Save"

**Via API**:
```bash
curl -X POST http://localhost:9089/api/config \
  -H "Content-Type: application/json" \
  -d '{"interval_days": 7}'
```

### Manual Scrape Trigger

**Via Dashboard**: Click "Run Now" button

**Via API**:
```bash
curl -X POST http://localhost:9089/api/control/run
```

## Development

### Building Locally

```bash
docker compose build
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f web
docker compose logs -f scheduler
```

### Running Tests

The scraper can be run standalone for testing:

```bash
python exchange_scraper_fixed.py
```

## Technical Stack

- **Backend**: Python 3.11+
- **Web Framework**: Flask
- **Scraping**: Playwright (Chromium)
- **Parsing**: BeautifulSoup4
- **Scheduling**: APScheduler
- **Excel**: openpyxl
- **Frontend**: HTML/CSS (Tailwind) + Vanilla JavaScript
- **Deployment**: Docker + Docker Compose

## Troubleshooting

### Scraper Not Running

1. Check scheduler logs: `docker compose logs scheduler`
2. Verify configuration: Check `data/config.json`
3. Check for control signals: Look in `data/` for `.signal` files

### Dashboard Not Loading

1. Check web service status: `docker compose ps`
2. Check web service logs: `docker compose logs web`
3. Verify port 9089 is not in use: `lsof -i :9089` (macOS/Linux)

### Reports Not Generating

1. Check for errors in scheduler logs
2. Verify `data/output/` directory exists and is writable
3. Check disk space

### Playwright/Browser Issues

If scraping fails with browser errors:

1. Rebuild container: `docker compose build --no-cache`
2. Check Dockerfile has all necessary dependencies
3. Try running with `HEADLESS=False` for debugging (requires code modification)

## Performance Considerations

- Full scrape of ~500 resources takes approximately 1-2 hours
- Each resource page requires a separate request
- 0.5 second delay between requests to be respectful to server
- Memory usage: ~500MB per container
- Disk usage: ~100KB per Excel report

## License

This project is provided as-is for tracking Ignition Exchange resources.

## Contributing

This is a self-contained project. Modify as needed for your specific requirements.

## Support

For issues or questions, refer to the project documentation or raise an issue in the repository.
