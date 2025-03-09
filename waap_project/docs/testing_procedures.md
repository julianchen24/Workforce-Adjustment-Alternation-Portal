# WAAP Testing Procedures

This document outlines the comprehensive testing procedures for the WAAP (Web Application for Agency Postings) application. It covers unit testing, integration testing, and end-to-end testing, as well as procedures for testing in staging and production environments.

## Table of Contents

1. [Testing Environment Setup](#testing-environment-setup)
2. [Unit Testing](#unit-testing)
3. [Integration Testing](#integration-testing)
4. [End-to-End Testing](#end-to-end-testing)
5. [Staging Environment Testing](#staging-environment-testing)
6. [Production Testing](#production-testing)
7. [Performance Testing](#performance-testing)
8. [Security Testing](#security-testing)
9. [Accessibility Testing](#accessibility-testing)
10. [Automated Testing](#automated-testing)

## Testing Environment Setup

### Local Development Environment

1. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up a test database:
   ```bash
   # PostgreSQL
   createdb waap_test
   ```

4. Configure test settings:
   ```bash
   # Use Django's test settings
   python manage.py test --settings=waap_project.settings
   ```

### Staging Environment

The staging environment should mirror the production environment as closely as possible:

1. Use the same database engine (PostgreSQL)
2. Use the same web server configuration (Nginx/Apache)
3. Use the same application server (Gunicorn)
4. Use similar (but not identical) domain names

## Unit Testing

Unit tests focus on testing individual components in isolation. The WAAP application includes unit tests for models, views, and forms.

### Running Unit Tests

```bash
# Run all unit tests
python manage.py test waap.tests

# Run specific test file
python manage.py test waap.tests.test_models
```

### Key Unit Test Areas

1. **Model Tests** (`tests.py`):
   - Test model creation
   - Test model validation
   - Test model methods

2. **View Tests** (`tests.py`):
   - Test view responses
   - Test view permissions
   - Test form handling

3. **Form Tests** (`tests.py`):
   - Test form validation
   - Test form submission

## Integration Testing

Integration tests verify that different components of the application work together correctly. The WAAP application includes integration tests that cover the interaction between different components.

### Running Integration Tests

```bash
# Run all integration tests
python manage.py test waap.tests_integration
```

### Key Integration Test Areas

1. **Authentication Flow** (`tests_integration.py`):
   - Test one-time token creation
   - Test login verification
   - Test session management

2. **Job Posting Workflow** (`tests_integration.py`):
   - Test job posting creation
   - Test job posting browsing and filtering
   - Test job posting deletion

3. **Contact System** (`tests_integration.py`):
   - Test contact form submission
   - Test email relay

4. **Moderation System** (`tests_integration.py`):
   - Test admin moderation actions
   - Test moderation status changes

5. **Auto-Expiration** (`tests_integration.py`):
   - Test job posting expiration
   - Test data anonymization

## End-to-End Testing

End-to-end tests simulate real user interactions with the application. The WAAP application includes comprehensive end-to-end tests that cover the entire user journey.

### Running End-to-End Tests

```bash
# Run the integrated workflow test
python manage.py test waap.tests_integration.IntegrationTest.test_integrated_workflow_with_moderation_and_expiration
```

### Key End-to-End Test Scenarios

1. **Complete User Journey** (`tests_integration.py`):
   - User authentication
   - Job posting creation
   - Public browsing
   - Contact form submission
   - Moderation
   - Expiration
   - Deletion

## Staging Environment Testing

Before deploying to production, conduct thorough testing in a staging environment that mirrors the production setup.

### Staging Deployment

1. Deploy the application to the staging environment using the deployment scripts:
   ```bash
   # For Azure
   ./deployment/azure/deploy_azure.sh

   # For internal servers
   ./deployment/internal/deploy_internal.sh
   ```

2. Apply migrations:
   ```bash
   python manage.py migrate --settings=waap_project.settings_production
   ```

3. Create test data:
   ```bash
   python manage.py loaddata test_data.json
   ```

### Staging Test Checklist

1. **Authentication**:
   - [ ] One-time token emails are sent correctly
   - [ ] Login verification works
   - [ ] Session management works

2. **Job Posting Management**:
   - [ ] Job postings can be created
   - [ ] Job postings can be viewed and filtered
   - [ ] Job postings can be deleted

3. **Contact System**:
   - [ ] Contact form works
   - [ ] Emails are sent correctly
   - [ ] CAPTCHA validation works

4. **Moderation System**:
   - [ ] Admins can flag job postings
   - [ ] Admins can approve job postings
   - [ ] Moderation status affects visibility

5. **Auto-Expiration**:
   - [ ] Scheduled task runs correctly
   - [ ] Expired job postings are anonymized
   - [ ] Expired job postings are not visible

6. **Security**:
   - [ ] SSL/TLS is configured correctly
   - [ ] CSRF protection works
   - [ ] Authentication is secure

## Production Testing

After deploying to production, conduct a final round of testing to ensure everything works correctly.

### Production Test Checklist

1. **Smoke Tests**:
   - [ ] Application loads correctly
   - [ ] All pages are accessible
   - [ ] No server errors

2. **Functionality Tests**:
   - [ ] Authentication works
   - [ ] Job posting management works
   - [ ] Contact system works
   - [ ] Moderation system works
   - [ ] Auto-expiration works

3. **Integration Tests**:
   - [ ] Email system works
   - [ ] Database connections are stable
   - [ ] Static files are served correctly

4. **Performance Tests**:
   - [ ] Page load times are acceptable
   - [ ] Database queries are optimized
   - [ ] Server resources are not overutilized

## Performance Testing

Performance testing ensures that the application can handle the expected load and performs well under stress.

### Tools

- **Apache JMeter**: For load testing
- **Django Debug Toolbar**: For query optimization
- **New Relic or Application Insights**: For production monitoring

### Performance Test Scenarios

1. **Load Testing**:
   - Simulate 100 concurrent users browsing job postings
   - Simulate 10 concurrent users creating job postings
   - Simulate 20 concurrent users submitting contact forms

2. **Stress Testing**:
   - Gradually increase load until the system breaks
   - Identify bottlenecks and optimize

3. **Endurance Testing**:
   - Run the application under normal load for an extended period
   - Monitor for memory leaks or performance degradation

## Security Testing

Security testing ensures that the application is secure and protected against common vulnerabilities.

### Security Test Checklist

1. **Authentication**:
   - [ ] One-time tokens are secure and time-limited
   - [ ] Sessions are secure
   - [ ] Password policies are enforced for admin users

2. **Authorization**:
   - [ ] Access controls are enforced
   - [ ] Users can only access their own data
   - [ ] Admin functions are protected

3. **Input Validation**:
   - [ ] Form inputs are validated
   - [ ] SQL injection is prevented
   - [ ] XSS attacks are prevented

4. **CSRF Protection**:
   - [ ] CSRF tokens are used for all forms
   - [ ] CSRF protection is enforced

5. **Data Protection**:
   - [ ] Sensitive data is encrypted
   - [ ] Personal data is anonymized when expired
   - [ ] Backups are secure

## Accessibility Testing

Accessibility testing ensures that the application is usable by people with disabilities.

### Accessibility Test Checklist

1. **Screen Reader Compatibility**:
   - [ ] All content is accessible via screen readers
   - [ ] ARIA attributes are used correctly
   - [ ] Alt text is provided for images

2. **Keyboard Navigation**:
   - [ ] All functionality is accessible via keyboard
   - [ ] Focus indicators are visible
   - [ ] Tab order is logical

3. **Color Contrast**:
   - [ ] Text has sufficient contrast
   - [ ] Color is not the only means of conveying information
   - [ ] UI elements have sufficient contrast

## Automated Testing

Automated testing ensures that tests are run consistently and frequently.

### Continuous Integration

Set up a CI/CD pipeline to run tests automatically:

1. **GitHub Actions**:
   ```yaml
   name: Django Tests

   on:
     push:
       branches: [ main ]
     pull_request:
       branches: [ main ]

   jobs:
     test:
       runs-on: ubuntu-latest
       services:
         postgres:
           image: postgres:12
           env:
             POSTGRES_USER: postgres
             POSTGRES_PASSWORD: postgres
             POSTGRES_DB: github_actions
           ports:
             - 5432:5432
           options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5

       steps:
       - uses: actions/checkout@v2
       - name: Set up Python
         uses: actions/setup-python@v2
         with:
           python-version: 3.12
       - name: Install Dependencies
         run: |
           python -m pip install --upgrade pip
           pip install -r requirements.txt
       - name: Run Tests
         run: |
           python manage.py test
         env:
           DATABASE_URL: postgres://postgres:postgres@localhost:5432/github_actions
   ```

2. **Scheduled Tests**:
   - Set up scheduled tests to run daily or weekly
   - Include end-to-end tests in scheduled runs

### Test Coverage

Monitor test coverage to ensure that all code is tested:

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run --source='.' manage.py test waap

# Generate coverage report
coverage report
```

## Conclusion

Following these testing procedures will ensure that the WAAP application is thoroughly tested and ready for production use. Regular testing should be conducted to maintain the quality and reliability of the application.
