# Event Management System

A robust RESTful API for event scheduling with collaborative editing features, built with FastAPI.

## Features

- Secure authentication with JWT tokens
- Role-based access control (Owner, Editor, Viewer)
- CRUD operations for events
- Recurring events support
- Conflict detection
- Batch operations
- Real-time notifications
- Version control with rollback capability
- Comprehensive changelog
- Event conflict resolution

## Prerequisites

- Python 3.9+
- PostgreSQL
- Redis (optional, for caching)
- Git

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd neo-events
```

2. Make the setup script executable:
```bash
chmod +x scripts/setup.sh
```

3. Run the setup script:
```bash
./scripts/setup.sh
```

The setup script will:
- Create a virtual environment
- Install dependencies
- Create a `.env` file from `.env.example`
- Initialize the database
- Run migrations

4. Edit the `.env` file with your configuration:
```env
# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=neo_events

# Security
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
```

5. Start the development server:
```bash
# Activate virtual environment (if not already activated)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Manual Setup

If you prefer to set up manually:

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
# Run database migrations
alembic upgrade head

# Initialize the database
python scripts/init_db.py
```

5. Run the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
neo-events/
├── alembic/              # Database migrations
├── app/
│   ├── api/             # API endpoints
│   ├── core/            # Core functionality
│   ├── crud/            # Database operations
│   ├── db/              # Database models and session
│   ├── schemas/         # Pydantic models
│   └── services/        # Business logic
├── scripts/             # Utility scripts
│   ├── init_db.py      # Database initialization
│   └── setup.sh        # Setup script
├── tests/               # Test files
├── .env                 # Environment variables
├── .env.example         # Example environment variables
├── alembic.ini          # Alembic configuration
├── requirements.txt     # Project dependencies
└── README.md           # This file
```

## Testing

Run tests with:
```bash
# Activate virtual environment (if not already activated)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run all tests
pytest

# Run tests with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_events.py

# Run tests with verbose output
pytest -v
```

## Database Migrations

To create a new migration:
```bash
alembic revision --autogenerate -m "description of changes"
```

To apply migrations:
```bash
alembic upgrade head
```

To rollback migrations:
```bash
alembic downgrade -1  # Rollback one version
alembic downgrade base  # Rollback all versions
```

## License

MIT 