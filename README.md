# theChallenge

A Flask web application for building personal day-based challenges, tracking daily tasks, and monitoring progress over time.

## Overview

`theChallenge` helps users create structured challenges (for example, 30-day habits), attach fixed daily tasks, add extra day-specific tasks, and mark progress from the challenge detail page.

The app includes:
- User registration and login
- Challenge creation with fixed recurring tasks
- Daily task management (add, complete, delete)
- Progress visualization per day (progress bars + line chart)
- Ownership checks so users can only access their own data

## Core Features

- Authentication:
  - Register and log in with hashed passwords (`werkzeug.security`)
  - Session-based access control

- Challenge Management:
  - Create a challenge with:
    - Name
    - Start date
    - Duration (days)
    - Fixed tasks repeated across challenge days
  - Delete an existing challenge

- Task Management:
  - Add dynamic (daily) tasks for the current day
  - Toggle completion state for tasks
  - Delete non-fixed tasks (current day only)

- Progress Tracking:
  - Day-level completion percentages
  - Line chart view of progress across all challenge days

- Security Controls:
  - CSRF protection for state-changing requests
  - Authorization checks for challenge and task ownership
  - Secure session cookie defaults (`HttpOnly`, `SameSite`)

## Tech Stack

- Backend: Flask
- Database: SQLite (via Flask-SQLAlchemy / SQLAlchemy)
- Migrations support: Flask-Migrate (Alembic)
- Frontend: Jinja2 templates + Vanilla JS + CSS
- Charting: Chart.js (CDN)

## Project Structure

```text
theChallenge/
├── app.py                    # Main Flask app (routes, models, security helpers)
├── reset_db.py               # Utility script to wipe and recreate DB tables
├── requirements.txt          # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css         # Global styling
│   └── js/
│       └── main.js           # Frontend interactions (modals, AJAX, chart updates)
├── templates/
│   ├── base.html             # Base layout
│   ├── home.html             # Dashboard / challenge list + create modal
│   ├── challenge_detail.html # Challenge timeline + day modal
│   ├── login.html
│   └── register.html
└── instance/
    └── theChallenge.db       # SQLite database file (generated at runtime)
```

## Requirements

- Python 3.10+ (recommended)
- pip

Dependencies (from `requirements.txt`):
- `Flask==3.1.2`
- `Flask-SQLAlchemy==3.1.1`
- `Flask-Migrate==4.0.7`

## Business Rules

- A user can only view and modify their own challenges/tasks.
- Task updates/deletions are restricted to the current challenge day.
- Fixed tasks cannot be deleted from day details.
- Challenge duration is validated (`1..365` days).
- Input fields are validated for length and required constraints.

## HTTP Routes Summary

- `GET /`  
  Home/dashboard (authenticated)

- `GET /register`, `POST /register`  
  User registration

- `GET /login`, `POST /login`  
  User login

- `GET /logout`  
  End user session

- `GET /view_challenge/<challenge_id>`  
  Challenge detail page

- `POST /create_challenge`  
  Create challenge with fixed tasks

- `POST /delete_challenge/<challenge_id>`  
  Delete challenge

- `POST /add_daily_task`  
  AJAX endpoint for adding a task to current day

- `POST /toggle_task/<task_id>`  
  AJAX endpoint for toggling task completion

- `POST /delete_task/<task_id>`  
  AJAX endpoint for deleting a non-fixed task

## Future Improvements

- Add full migration workflow docs (`flask db init/migrate/upgrade`)
- Add automated test suite (unit + integration)
- Add role-based permissions and audit logs
- Add i18n support and locale switching
