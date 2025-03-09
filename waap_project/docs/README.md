# WAAP Deployment and Testing Documentation

This directory contains comprehensive documentation for deploying, testing, and maintaining the WAAP (Web Application for Agency Postings) application.

## Documentation Overview

- [Deployment Guide](deployment_guide.md): Comprehensive guide for deploying the application to different environments
- [Testing Procedures](testing_procedures.md): Detailed testing procedures for ensuring application quality

## Deployment Options

The WAAP application can be deployed to:

1. **Microsoft Azure**: Cloud-based deployment
   - [Azure Deployment Guide](../deployment/azure/README.md)
   - [Azure Deployment Script](../deployment/azure/deploy_azure.sh)

2. **Internal Government Servers**: On-premises deployment
   - [Internal Server Deployment Guide](../deployment/internal/README.md)
   - [Internal Server Deployment Script](../deployment/internal/deploy_internal.sh)

## Testing Resources

- [End-to-End Testing Script](../scripts/run_e2e_tests.sh): Script for running comprehensive end-to-end tests in a staging environment

## Production Settings

The application includes a production settings file that configures the application for secure production use:

- [Production Settings](../waap_project/settings_production.py): Django settings optimized for production environments

## Key Features

The WAAP application includes several key features that are covered in the deployment and testing documentation:

1. **Authentication System**: Secure one-time token-based authentication
2. **Job Posting Management**: Creation, viewing, and deletion of job postings
3. **Contact System**: Secure communication between users
4. **Moderation System**: Administrative moderation of job postings
5. **Auto-Expiration System**: Automatic expiration and anonymization of old job postings

## Scheduled Tasks

The application includes a scheduled task for automatically expiring and anonymizing old job postings:

- [Expire Job Postings Command](../waap/management/commands/expire_job_postings.py): Management command for expiring job postings
- [Scheduled Task Documentation](../waap/management/commands/README.md): Documentation for setting up and running the scheduled task

## Integration Testing

The application includes comprehensive integration tests that verify the correct functioning of all components:

- [Integration Tests](../waap/tests_integration.py): End-to-end tests for the application
- [Integration Documentation](../waap/INTEGRATION.md): Documentation for the integration between different components

## Quick Start

To quickly deploy and test the application:

1. Choose a deployment option (Azure or Internal Server)
2. Follow the deployment guide for your chosen option
3. Run the end-to-end tests to verify the deployment
4. Set up the scheduled task for auto-expiration

## Security Considerations

The deployment documentation includes important security considerations:

1. **Environment Variables**: Secure storage of sensitive configuration
2. **SSL/TLS**: Secure communication
3. **Database Security**: Secure database configuration
4. **Authentication Security**: Secure authentication system
5. **Data Protection**: Anonymization of expired data

## Maintenance

Regular maintenance tasks are documented in the deployment guide:

1. **Database Maintenance**: Regular database optimization
2. **Log Rotation**: Management of log files
3. **Backup and Recovery**: Regular backups and recovery procedures
4. **Monitoring**: Application and system monitoring

## Troubleshooting

Common issues and their solutions are documented in the deployment guide:

1. **Application Issues**: Troubleshooting application problems
2. **Database Issues**: Troubleshooting database problems
3. **Web Server Issues**: Troubleshooting web server problems
4. **Email Issues**: Troubleshooting email delivery problems
5. **Scheduled Task Issues**: Troubleshooting scheduled task problems
