# Workforce Adjustment Alternation Portal (WAAP)

A Django-based web application for managing workforce adjustments and alternations.

![unnamed](https://github.com/user-attachments/assets/3cfcfafe-c4f0-444a-afe3-64433e557593)
![unnamed-1](https://github.com/user-attachments/assets/02f954d4-ba29-4431-bc7d-2c1167f96e93)


## Setup Instructions

### Prerequisites

- Python 3.12+
- PostgreSQL

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/julianchen24/Workforce-Adjustment-Alternation-Portal.git
   cd waap_project
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the database using the setup script:
   ```bash
   python setup_db.py
   ```
   This script will:
   - Check if PostgreSQL is installed
   - Create a PostgreSQL database
   - Update the database settings in `waap_project/settings.py`
   - Apply migrations
   - Create a superuser

   Alternatively, you can configure the database manually:
   - Create a PostgreSQL database named `waap_db`
   - Update the database settings in `waap_project/settings.py` if needed
   - Apply migrations: `python manage.py makemigrations && python manage.py migrate`
   - Create a superuser: `python manage.py createsuperuser`

### Verifying Setup

You can verify that your project is properly set up by running:
```bash
python check_setup.py
```

This script will check:
- Python version compatibility
- Django installation
- PostgreSQL installation
- Database connection
- Migration status
- Static files configuration

### Running the Development Server

```bash
python manage.py runserver
```

The application will be available at http://127.0.0.1:8000/

### Running Tests

```bash
python manage.py test
```

