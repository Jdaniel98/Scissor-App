# FastAPI URL Shortener

A web application built with FastAPI for shortening URLs, featuring a user-friendly interface and database integration.

## Features

- URL shortening functionality
- FastAPI backend
- Jinja2 templating for frontend
- CORS middleware for cross-origin requests
- Static file serving
- Database integration with SQLAlchemy

## Requirements

- Python 3.7+
- FastAPI
- Jinja2
- SQLAlchemy
- (Other dependencies as needed)

## Installation

1. Clone this repository:
   ```
   https://github.com/Jdaniel98/Scissor-App.git
   cd fastapi-url-shortener
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Project Structure

```
app/
├── main.py
├── database/
│   ├── db.py
│   └── models.py
├── routers/
│   └── url.py
├── static/
├── templates/
│   └── index.html
└── templates.py
```

## Usage

To run the application:

```
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`.

## API Endpoints

- `GET /`: Home page
- (Other endpoints defined in `url_router`)

## Configuration

- CORS is enabled for all origins (`"*"`). Modify the `origins` list in `main.py` to restrict access if needed.
- Database models are defined in `app/database/models.py` and use SQLAlchemy ORM.
- Static files are served from the `app/static` directory.
- HTML templates are located in the `app/templates` directory and use Jinja2.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This project is provided as-is, without any guarantees. Ensure to follow best practices for security and performance when deploying to a production environment.
