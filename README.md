# Cian Apartment Tracker

A web application for tracking and analyzing apartment listings from Cian.ru.

## Features

- Scrapes apartment listings from Cian.ru
- Displays listings in a user-friendly dashboard
- Calculates distances from a reference location
- Tracks price changes over time
- Refreshes data automatically

## Components

- **Dashboard**: Web interface built with Dash
- **Scheduler**: Background process that triggers scraping at regular intervals
- **Parser**: Scrapes apartment data from Cian.ru
- **Distance Calculator**: Calculates distances between apartments and a reference location

## Deployment

### Local Development

1. Clone the repository
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Run the application:
```
python main.py
```

### Render.com Deployment

This application is configured for deployment on Render.com using the provided files:

- `requirements.txt`: Lists all dependencies
- `Procfile`: Specifies how to run the application
- `wsgi.py`: Entry point for the web server
- `gunicorn_config.py`: Configuration for Gunicorn
- `render.yaml`: Blueprint for Render.com services

## Project Structure

- `main.py`: Main entry point that starts the scheduler and dashboard
- `cian_dashboard.py`: Dash application for the web interface
- `cian_scheduler.py`: Scheduler for periodic scraping
- `cian_parser.py`: Scraper for Cian.ru
- `distance.py`: Utilities for calculating distances
- `table_config.py`: Configuration for the data table
- `selenium_helper.py`: Helper for Selenium in cloud environments

## Data Storage

The application stores data in CSV and JSON files:
- `cian_apartments.csv`: Main data file
- `cian_apartments.json`: JSON representation of the data

## Logs

Logs are stored in the `logs/` directory.

## License

This project is licensed under the MIT License - see the LICENSE file for details.