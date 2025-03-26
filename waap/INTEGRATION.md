# WAAP Integration and End-to-End Testing Documentation

This document provides an overview of how the various components of the WAAP (Web Application for Anonymous Postings) application are integrated and how to run the comprehensive end-to-end tests.

## 1. Component Integration

The WAAP application consists of several core components that work together to provide a complete job posting platform:

### Authentication System
- **One-time login tokens**: Users receive secure, time-limited tokens via email
- **Session-based authentication**: After token verification, users are authenticated via session
- **Integration point**: `OneTimeToken` model connects to `WaapUser` model through email

### Job Posting Management
- **Creation**: Authenticated users can create job postings
- **Viewing**: Public users can browse and filter job postings
- **Deletion**: Creators can request deletion via secure tokens
- **Integration point**: `JobPosting` model connects to `WaapUser` through the `creator` field

### Contact System
- **Contact form**: Public users can contact job posting owners
- **Email relay**: Messages are sent via the application to protect privacy
- **Integration point**: `ContactMessage` model connects to `JobPosting` through a foreign key

### Moderation System
- **Admin interface**: Administrators can review and moderate job postings
- **Status tracking**: Postings can be approved, flagged, marked inappropriate, or removed
- **Integration point**: `JobPosting` model includes moderation fields and status

### Auto-Expiration System
- **Management command**: `expire_job_postings` runs periodically
- **Data anonymization**: Expired postings have personal data removed
- **Integration point**: Command operates on `JobPosting` model based on expiration date

## 2. Data Flow

The integration of these components creates the following data flow:

1. User requests a one-time login token → Token is created and emailed
2. User clicks the token link → User is authenticated and session is created
3. User creates a job posting → Posting is stored with user as creator
4. Public users browse postings → Only approved, non-expired postings are shown
5. Public user contacts posting owner → Contact message is created and relayed
6. Creator requests deletion → Deletion token is created and emailed
7. Creator confirms deletion → Posting is permanently deleted
8. Auto-expiration runs → Expired postings are anonymized

## 3. End-to-End Tests

The integration tests in `tests_integration.py` simulate the entire workflow of the application, ensuring that all components work together correctly.

### Test Structure

The integration tests are organized into four main test cases:

1. **test_end_to_end_workflow**: Tests the complete user journey from login to deletion
2. **test_admin_moderation_workflow**: Tests the admin moderation functionality
3. **test_auto_expiration_workflow**: Tests the auto-expiration functionality
4. **test_integrated_workflow_with_moderation_and_expiration**: Tests all components working together

### Running the Tests

To run the integration tests:

```bash
# Activate the virtual environment
source waap_env/bin/activate  # Linux/macOS
waap_env\Scripts\activate     # Windows

# Navigate to the project directory
cd waap_project

# Run the integration tests
python manage.py test waap.tests_integration

# Run all tests (unit tests and integration tests)
python manage.py test waap
```

### Test Configuration

The integration tests use Django's testing framework, which:

1. Creates a test database (separate from your development database)
2. Runs each test in a transaction that is rolled back after the test
3. Mocks certain functionality (like email sending and CAPTCHA validation)

No additional configuration is required to run the tests, as they are self-contained.

## 4. Scheduled Tasks

The auto-expiration functionality relies on the `expire_job_postings` management command being run periodically. This can be configured using:

- **Cron** (Linux/Unix/macOS)
- **Windows Task Scheduler** (Windows)
- **Django-crontab** (Django-specific solution)
- **Celery Beat** (Production environments)

See `waap/management/commands/README.md` for detailed setup instructions.

## 5. Security Considerations

The integration of components includes several security measures:

- **One-time tokens**: Login and deletion tokens are single-use and time-limited
- **Email validation**: Only government email addresses (.ca domain) can register
- **CAPTCHA protection**: Contact form includes CAPTCHA to prevent spam
- **Moderation system**: Administrators can review and remove inappropriate content
- **Data anonymization**: Expired postings have personal data removed automatically
- **Email relay**: Contact messages are sent through the application to protect privacy

## 6. Troubleshooting

If the integration tests fail, check the following:

1. **Database migrations**: Ensure all migrations have been applied
2. **Environment variables**: Check that required environment variables are set
3. **Dependencies**: Verify all required packages are installed
4. **Permissions**: Ensure the application has necessary permissions (file system, email)
5. **Test isolation**: Check if tests are interfering with each other

## 7. Future Improvements

Potential improvements to the integration and testing:

1. **API testing**: Add tests for any future API endpoints
2. **Performance testing**: Add tests for performance under load
3. **Browser testing**: Add Selenium tests for frontend functionality
4. **Continuous integration**: Set up CI/CD pipeline for automated testing
5. **Monitoring**: Add monitoring for the auto-expiration process
