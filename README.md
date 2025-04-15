# OnlyFans Dashboard

A Django-based dashboard for visualizing OnlyFans statistics and analytics.

## Features

- Real-time statistics for posts, followers, and mentions
- Interactive charts showing trends over time
- Detailed view of scheduled posts
- Comparison of actual vs scheduled posts
- Historical data analysis

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd of_dashboard
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Make sure your SQLite database file (`onlyfans_notifications.db`) is in the project root directory.

## Running the Project

1. Make sure your virtual environment is activated.

2. Run the development server:
```bash
python manage.py runserver
```

3. Open your web browser and navigate to:
```
http://127.0.0.1:8000/
```

## Project Structure

```
of_dashboard/
├── dashboard/              # Main app directory
│   ├── models.py          # Database models
│   ├── views.py           # View logic
│   └── urls.py            # URL routing
├── templates/             # HTML templates
│   ├── base.html         # Base template
│   └── dashboard/        # Dashboard templates
├── static/               # Static files
├── manage.py             # Django management script
└── requirements.txt      # Project dependencies
```

## Notes

- The dashboard uses the existing SQLite database (`onlyfans_notifications.db`) and does not create or modify any tables
- All models are set with `managed = False` to prevent Django from attempting to create or modify the database schema
- The project uses Bootstrap for styling and Plotly for interactive charts 