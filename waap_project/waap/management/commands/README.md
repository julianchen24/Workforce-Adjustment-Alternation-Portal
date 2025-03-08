# Job Posting Auto-Expiration & Data Anonymization

This directory contains management commands for the WAAP application, including the `expire_job_postings` command that automatically expires and anonymizes job postings older than 30 days.

## expire_job_postings Command

The `expire_job_postings` command checks for job postings with an expiration date in the past and anonymizes them by removing personal identifiers such as contact email addresses.

### Usage

To run the command manually:

```bash
python manage.py expire_job_postings
```

To run the command in dry-run mode (no changes will be made):

```bash
python manage.py expire_job_postings --dry-run
```

## Setting Up Periodic Execution

### Option 1: Using Cron (Linux/Unix/macOS)

To run the command automatically every day at midnight:

1. Open your crontab file:

```bash
crontab -e
```

2. Add the following line (adjust the paths as needed):

```
0 0 * * * cd /path/to/waap_project && /path/to/python manage.py expire_job_postings >> /path/to/logs/expire_job_postings.log 2>&1
```

### Option 2: Using Windows Task Scheduler

1. Open Task Scheduler
2. Click "Create Basic Task"
3. Enter a name (e.g., "WAAP Job Posting Expiration") and description
4. Set the trigger to run daily
5. Set the action to "Start a program"
6. Program/script: `C:\path\to\python.exe`
7. Add arguments: `C:\path\to\waap_project\manage.py expire_job_postings`
8. Set the "Start in" directory to your project directory: `C:\path\to\waap_project`

### Option 3: Using Django's Built-in Scheduler (django-crontab)

1. Install django-crontab:

```bash
pip install django-crontab
```

2. Add 'django_crontab' to INSTALLED_APPS in settings.py:

```python
INSTALLED_APPS = [
    # ...
    'django_crontab',
    # ...
]
```

3. Add the CRONJOBS setting to settings.py:

```python
CRONJOBS = [
    ('0 0 * * *', 'django.core.management.call_command', ['expire_job_postings']),
]
```

4. Apply the crontab:

```bash
python manage.py crontab add
```

### Option 4: Using a Production-Ready Task Queue (Celery)

For production environments, consider using Celery with a scheduler like Celery Beat:

1. Install Celery and related packages:

```bash
pip install celery django-celery-beat
```

2. Configure Celery in your project (see Celery documentation)

3. Create a periodic task in Celery Beat to run the command daily

## Monitoring

It's recommended to set up logging for the command to monitor its execution. You can modify the command to log to a file or integrate with your application's logging system.

The command already outputs information about the job postings it processes, which will be captured in the logs if you set up the cron job as shown above.
