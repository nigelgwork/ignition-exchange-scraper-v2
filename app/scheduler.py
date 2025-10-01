"""
Scheduler service for running scraper on schedule
"""
import sys
import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Add parent directory to path so we can import exchange_scraper_fixed
sys.path.insert(0, str(Path(__file__).parent.parent))

from exchange_scraper_fixed import ScraperEngine
from app.comparison import compare_resources, get_comparison_stats
from app.excel_generator import create_excel_report, generate_filename
from app.notifications import notify_scrape_complete

# Paths
DATA_DIR = Path('/data')
STATE_FILE = DATA_DIR / 'state.json'
LOG_FILE = DATA_DIR / 'activity.log'
CONFIG_FILE = DATA_DIR / 'config.json'
CACHE_FILE = DATA_DIR / 'past_results_cache.json'
OUTPUT_DIR = DATA_DIR / 'output'
HISTORY_FILE = DATA_DIR / 'job_history.json'

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Global scraper instance
current_scraper = None
scraper_lock = threading.Lock()


def append_log(message: str, level: str = 'info'):
    """Append log entry to file"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'message': message,
        'level': level
    }

    print(f"[{level.upper()}] {message}")

    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')


def load_state() -> dict:
    """Load state from file"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass

    return {
        'status': 'idle',
        'progress': {'current': 0, 'total': 0, 'percentage': 0, 'current_item': ''},
        'current_job': None,
        'last_run': None,
        'next_run': None,
        'elapsed_seconds': 0,
        'estimated_remaining_seconds': 0
    }


def save_state(state: dict):
    """Save state to file"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_config() -> dict:
    """Load configuration"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Migrate old interval_hours to interval_days
                if 'interval_hours' in config and 'interval_days' not in config:
                    config['interval_days'] = config['interval_hours'] / 24
                    config.pop('interval_hours', None)
                return config
        except:
            pass

    return {'interval_days': 7, 'enabled': True}


def load_past_results() -> list:
    """Load past results from cache"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass

    return []


def save_past_results(results: list):
    """Save results to cache"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(results, f, indent=2)


def load_job_history() -> list:
    """Load job history"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass

    return []


def save_job_history(history: list):
    """Save job history"""
    # Keep only last 50 jobs
    history = history[-50:]

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def check_control_signals():
    """Check for control signal files and return action"""
    for action in ['run', 'pause', 'stop', 'resume']:
        signal_file = DATA_DIR / f'control_{action}.signal'
        if signal_file.exists():
            signal_file.unlink()
            return action
    return None


def progress_callback(data: dict):
    """Callback for scraper progress updates"""
    state = load_state()

    if data['type'] == 'log':
        append_log(data['message'], data.get('level', 'info'))

    elif data['type'] == 'progress':
        state['progress']['current'] = data['current']
        state['progress']['total'] = data['total']
        state['progress']['percentage'] = int((data['current'] / data['total'] * 100) if data['total'] > 0 else 0)
        state['progress']['current_item'] = data.get('current_item', '')

        # Update elapsed and estimated time
        if state['current_job'] and state['current_job'].get('start_time'):
            start_time = datetime.fromisoformat(state['current_job']['start_time'])
            elapsed = (datetime.now() - start_time).total_seconds()
            state['elapsed_seconds'] = int(elapsed)

            # Estimate remaining time
            if data['current'] > 0:
                rate = elapsed / data['current']
                remaining = rate * (data['total'] - data['current'])
                state['estimated_remaining_seconds'] = int(remaining)

        save_state(state)


def run_scraper_job():
    """Run the scraper job"""
    global current_scraper

    append_log('Starting scraper job...')

    state = load_state()
    state['status'] = 'running'
    state['current_job'] = {
        'start_time': datetime.now().isoformat(),
        'errors': 0
    }
    state['progress'] = {'current': 0, 'total': 0, 'percentage': 0, 'current_item': 'Initializing...'}
    state['elapsed_seconds'] = 0
    state['estimated_remaining_seconds'] = 0
    save_state(state)

    job_start = datetime.now()
    errors = 0
    current_results = []

    try:
        # Create scraper instance
        with scraper_lock:
            current_scraper = ScraperEngine(headless=True, progress_callback=progress_callback)

        append_log('Scraping Exchange resources...')

        # Run scraper
        current_results = current_scraper.scrape_all_resources()

        append_log(f'Scraping complete. Found {len(current_results)} resources.')

        # Check if stopped
        if current_scraper.should_stop:
            append_log('Job was stopped by user', 'warning')
            state = load_state()
            state['status'] = 'stopped'
            state['current_job'] = None
            save_state(state)
            return

        # Load past results for comparison
        past_results = load_past_results()
        append_log(f'Loaded {len(past_results)} past results for comparison')

        # Compare results
        updated_results = compare_resources(current_results, past_results)
        append_log(f'Found {len(updated_results)} new or updated resources')

        # Get stats
        stats = get_comparison_stats(current_results, past_results, updated_results)

        # Generate Excel report
        filename = generate_filename()
        output_path = OUTPUT_DIR / filename
        append_log(f'Generating Excel report: {filename}')

        create_excel_report(updated_results, current_results, past_results, output_path)
        append_log(f'Excel report saved: {output_path}')

        # Update cache
        save_past_results(current_results)
        append_log('Updated cache with current results')

        # Send notifications
        config = load_config()
        if config.get('notifications'):
            append_log('Sending notifications...')
            notif_results = notify_scrape_complete(config.get('notifications'), stats, output_path)
            for channel, success in notif_results.items():
                if success:
                    append_log(f'  ✓ {channel.capitalize()} notification sent')
                elif config.get('notifications', {}).get(channel, {}).get('enabled'):
                    append_log(f'  ✗ {channel.capitalize()} notification failed', 'warning')

        # Update job history
        job_end = datetime.now()
        duration = (job_end - job_start).total_seconds()

        history = load_job_history()
        history.append({
            'date': job_start.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': int(duration),
            'duration_formatted': format_duration(duration),
            'status': 'done',
            'count': len(current_results),
            'errors': errors,
            'new_count': stats['new_count'],
            'updated_count': stats['modified_count']
        })
        save_job_history(history)

        append_log(f'Job completed successfully in {format_duration(duration)}')

    except Exception as e:
        append_log(f'Job failed with error: {str(e)}', 'error')
        errors += 1

        # Update job history with error
        job_end = datetime.now()
        duration = (job_end - job_start).total_seconds()

        history = load_job_history()
        history.append({
            'date': job_start.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': int(duration),
            'duration_formatted': format_duration(duration),
            'status': 'failed',
            'count': len(current_results),
            'errors': errors,
            'error_message': str(e)
        })
        save_job_history(history)

    finally:
        # Update state
        state = load_state()
        state['status'] = 'done' if errors == 0 else 'failed'
        state['last_run'] = datetime.now().isoformat()
        state['current_job'] = None
        state['progress'] = {'current': 0, 'total': 0, 'percentage': 0, 'current_item': ''}

        # Calculate next run
        config = load_config()
        next_run = datetime.now() + timedelta(days=config.get('interval_days', 7))
        state['next_run'] = next_run.isoformat()

        save_state(state)

        with scraper_lock:
            current_scraper = None


def format_duration(seconds: float) -> str:
    """Format duration in human readable form"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def monitor_control_signals():
    """Monitor control signals in background"""
    global current_scraper

    while True:
        time.sleep(1)

        action = check_control_signals()

        if action == 'run':
            append_log('Manual run requested')
            threading.Thread(target=run_scraper_job, daemon=True).start()

        elif action == 'pause':
            with scraper_lock:
                if current_scraper:
                    current_scraper.pause()
                    state = load_state()
                    state['status'] = 'paused'
                    save_state(state)

        elif action == 'stop':
            with scraper_lock:
                if current_scraper:
                    current_scraper.stop()

        elif action == 'resume':
            with scraper_lock:
                if current_scraper:
                    current_scraper.resume()
                    state = load_state()
                    state['status'] = 'running'
                    save_state(state)


def main():
    """Main scheduler loop"""
    append_log('Scheduler service starting...')

    # Initialize state
    state = load_state()
    state['status'] = 'idle'
    save_state(state)

    # Load configuration
    config = load_config()
    interval_days = config.get('interval_days', 7)
    append_log(f'Configuration: interval={interval_days} days, enabled={config["enabled"]}')

    # Calculate next run
    next_run = datetime.now() + timedelta(days=interval_days)
    state['next_run'] = next_run.isoformat()
    save_state(state)

    # Start scheduler
    scheduler = BackgroundScheduler()

    # Add job with interval trigger (convert days to hours for APScheduler)
    scheduler.add_job(
        run_scraper_job,
        trigger=IntervalTrigger(hours=interval_days * 24),
        id='scraper_job',
        name='Exchange Scraper Job',
        replace_existing=True,
        next_run_time=next_run
    )

    scheduler.start()
    append_log('Scheduler started')

    # Start control signal monitor in background thread
    monitor_thread = threading.Thread(target=monitor_control_signals, daemon=True)
    monitor_thread.start()

    # Keep running
    try:
        while True:
            time.sleep(10)

            # Reload config periodically and update scheduler if changed
            new_config = load_config()
            new_interval_days = new_config.get('interval_days', 7)
            if new_interval_days != config.get('interval_days', 7):
                append_log(f'Config changed, updating schedule to {new_interval_days} days')
                config = new_config

                # Reschedule job (convert days to hours for APScheduler)
                scheduler.reschedule_job(
                    'scraper_job',
                    trigger=IntervalTrigger(hours=new_interval_days * 24)
                )

                # Update next run time
                state = load_state()
                next_run = datetime.now() + timedelta(days=new_interval_days)
                state['next_run'] = next_run.isoformat()
                save_state(state)

    except (KeyboardInterrupt, SystemExit):
        append_log('Scheduler shutting down...')
        scheduler.shutdown()


if __name__ == '__main__':
    main()
