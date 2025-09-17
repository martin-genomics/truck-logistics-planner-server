# Route Planner with Local Geocoding

A Django-based route planning application with local geocoding capabilities.

## Features

- Local geocoding service for address lookups
- Route planning functionality
- Environment-based configuration
- SQLite database for development

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd windsurf-project
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Configuration

Copy `.env.example` to `.env` and update the following variables:

```
# Database settings
DATABASE_NAME=db.sqlite3
DATABASE_USER=
DATABASE_PASSWORD=
DATABASE_HOST=
DATABASE_PORT=

# Other settings
DEBUG=True
SECRET_KEY=your-secret-key-here
```

## Running the Application

1. Apply database migrations:
   ```bash
   python manage.py migrate
   ```

2. Start the development server:
   ```bash
   python manage.py runserver
   ```

3. Open your browser to `http://127.0.0.1:8000/`

## Project Structure

```
windsurf-project/
├── route_planner/       # Django project settings
├── routes/              # Main application
│   ├── services/        # Business logic and services
│   └── ...
├── manage.py            # Django management script
├── requirements.txt     # Project dependencies
└── .env                 # Environment variables (git-ignored)
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Django Web Framework
- Other dependencies listed in requirements.txt
