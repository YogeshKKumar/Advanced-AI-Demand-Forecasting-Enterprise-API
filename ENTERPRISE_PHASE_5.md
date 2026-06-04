# Enterprise Phase 5 Upgrade

This phase adds smart automation, enterprise integration management, AI recommendation services, forecast insight APIs, profile and account management, configurable alerts, dashboard widgets, and additional security controls.

## Backend

- Smart forecasting schedules: `/api/automation/schedules`, `/api/automation/run-due`
- ERP, inventory, external API integrations and webhooks: `/api/integrations`, `/api/webhooks`
- Advanced AI insights: `/api/ai/{dataset_id}/enterprise-insights`
- Forecast trends and confidence recommendations: `/api/forecast/{dataset_id}/insights`
- Profile, password reset, alert rules, widgets, and dashboard summary APIs
- In-memory API rate limiting, stronger password hashing defaults, upload size validation, admin account status management

## Frontend

- Automation workspace
- Integrations workspace
- Profile, alert, and widget settings workspace
- Reusable `DataTable` and `Modal` components
- Additional AI insight cards and forecast recommendation section

## Production Notes

For production, replace SQLite with PostgreSQL, move scheduled execution to Celery/RQ/APScheduler, store connector secrets in a vault, and send email notifications through SMTP or a managed provider.
