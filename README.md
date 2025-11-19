# Semhas Notifier

A web application that monitors the SILAT (Sistem Informasi Layanan Terintegrasi) website at Fatisda UNS and sends email notifications to subscribers whenever new thesis defense schedules are posted.

**Live Website:** https://semhas-notifier.riyaldi.qzz.io

## Features

- Automated website scraping every 30 minutes
- Email notifications for new thesis defense schedules
- One-click unsubscribe functionality
- Email subscriber database management
- Secure token-based unsubscribe links
- HTML and plain text email support
- Docker containerization for easy deployment
- Bulk email sending with SMTP

## Tech Stack

- **Backend:** Python 3.9+
- **Framework:** Flask 3.0.0
- **Web Server:** Gunicorn
- **Database:** SQLite
- **Web Scraping:** BeautifulSoup 4.12.2
- **HTTP Requests:** Requests 2.31.0
- **Task Scheduling:** APScheduler 3.10.4
- **Email Authentication:** python-dotenv 1.2.1
- **Token Generation:** itsdangerous

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- SMTP server credentials (for email functionality)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/riyhs/semhas-notifier.git
cd SemhasScraper
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with the following variables:
```
SMTP_SERVER=your_smtp_server
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_SENDER_EMAIL=your_email@gmail.com
SMTP_SENDER_NAME=Your Name
SECRET_KEY=your_secret_key_here
APP_BASE_URL=http://localhost:5000
```

5. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Docker Deployment

Build and run using Docker:

```bash
docker build -t semhas-notifier .
```
Run the container (Linux/Mac/Git Bash):
```bash
docker run -p 5000:5000 --env-file .env -v $(pwd)/data:/app/data semhas-notifier
```

Run the container (Windows PowerShell):
```bash
docker run -p 5000:5000 --env-file .env -v ${PWD}/data:/app/data semhas-notifier
```

Note: The -v flag mounts the local data directory to the container to ensure the SQLite database and scraping state persist across restarts.

## How It Works

1. **Scraping:** Every 30 minutes, the scheduler automatically scrapes the SILAT website to fetch the latest thesis defense schedules
2. **Change Detection:** New entries are compared against the previously saved data
3. **Notifications:** If new schedules are found, email notifications are sent to all subscribers
4. **Subscription Management:** Users can subscribe via the web interface or unsubscribe using secure tokens

## API Endpoints

- `GET /` - Homepage with subscription form
- `POST /` - Subscribe email to notifications
- `GET /unsubscribe/<token>` - Unsubscribe using token

## Database Schema

### subscribers table
```
CREATE TABLE subscribers (
    email TEXT PRIMARY KEY
)
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| SMTP_SERVER | SMTP server address | smtp.gmail.com |
| SMTP_PORT | SMTP port number | 587 |
| SMTP_USER | SMTP login username | your_email@gmail.com |
| SMTP_PASSWORD | SMTP login password | your_app_password |
| SMTP_SENDER_EMAIL | Sender email address | noreply@example.com |
| SMTP_SENDER_NAME | Sender display name | Semhas Notifier |
| SECRET_KEY | Flask secret key for sessions | random_string |
| APP_BASE_URL | Application base URL | https://semhas-notifier.riyaldi.qzz.io |

## File Structure

```
SemhasScraper/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── LICENSE               # License file
├── README.md            # This file
├── .gitignore           # Git ignore rules
├── data/
│   ├── data_terakhir.json       # Latest scraped data state
│   └── subscribers.db           # SQLite database for subscribers
└── templates/
    ├── index.html               # Homepage template
    ├── email_template.html      # Email notification template
    └── unsubscribe.html         # Unsubscribe confirmation template
```

## Email Features

- **RFC 6852 Compliance:** Implements List-Unsubscribe header for one-click unsubscribe
- **Auto-Reply Suppression:** Prevents auto-reply messages
- **Bulk Email Headers:** Proper Precedence and X-Auto-Response-Suppress headers
- **Token Expiry:** Unsubscribe tokens expire after 7 days

## Logging

The application logs all activities including:
- Scraper execution
- Email sending status
- Error messages
- Subscriber count updates

Logs are output to the console with timestamps and severity levels.

## Security Notes

- Never commit the `.env` file to version control
- Use environment variables for all sensitive credentials
- Unsubscribe tokens are cryptographically signed and time-limited
- Email addresses are stored securely in SQLite database

## Author

Created by [Riyaldi](https://github.com/riyhs)

## License

See LICENSE file for details.
