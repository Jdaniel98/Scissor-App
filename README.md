Scissor - URL Shortener
Scissor is a powerful URL shortening service built with Python, designed to disrupt the URL-shortening industry. Our motto: "Brief is the new black."
Table of Contents

Features
Technologies Used
Detailed Implementation
Project Structure
Setup and Installation
Usage
API Documentation
Testing
Performance Considerations
Security Considerations
Contributing
License

Features

URL Shortening: Generate short URLs from long ones.
Custom URLs: Create branded, customized short links.
QR Code Generation: Generate QR codes for shortened URLs.
Analytics: Track click statistics and sources.
Link History: View and manage previously created links.

Technologies Used

Python 3.9+: The core programming language.
FastAPI: A modern, fast (high-performance) web framework for building APIs with Python 3.6+ based on standard Python type hints.
SQLite: A C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine.
SQLAlchemy: The Python SQL toolkit and Object-Relational Mapping (ORM) library.
Pydantic: Data validation and settings management using Python type annotations.
Redis: An open source, in-memory data structure store, used as a database, cache, and message broker.
aioredis: An async Redis client for Python.
qrcode: A pure Python QR Code generator.
pytest: A framework for writing small, readable tests.
uvicorn: A lightning-fast ASGI server, for running the FastAPI application.
Alembic: A lightweight database migration tool for usage with SQLAlchemy.

Detailed Implementation
URL Shortening
The URL shortening process involves several steps:

URL Validation: We use Pydantic's HttpUrl type for input validation, ensuring that only valid URLs are processed.
Short Code Generation: We implement a base62 encoding algorithm to generate short, unique identifiers. This allows for a large number of possible combinations while keeping the short URLs compact.
pythonCopyimport string
import random

CHARACTERS = string.ascii_letters + string.digits

def generate_short_code(length=6):
    return ''.join(random.choice(CHARACTERS) for _ in range(length))

Collision Handling: We implement a retry mechanism to handle the rare case of collisions when generating short codes.
Database Storage: We use SQLAlchemy to define a URL model and store the mapping between short codes and original URLs.
pythonCopyfrom sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class URL(Base):
    __tablename__ = "urls"

    short_code = Column(String, primary_key=True, index=True)
    original_url = Column(String, index=True)
    created_at = Column(DateTime, server_default=func.now())


Custom URLs
Custom URL functionality is implemented as follows:

Input Validation: We use a Pydantic model to validate the custom URL input, ensuring it meets our criteria (e.g., allowed characters, length restrictions).
Availability Check: Before creating a custom URL, we check if it's already in use.
Database Storage: Custom URLs are stored in the same URL table, with an additional flag to distinguish them from auto-generated short URLs.

QR Code Generation
QR code generation is implemented as an asynchronous task:

We use the qrcode library to generate QR codes.
QR code generation is offloaded to a FastAPI background task to prevent blocking the main request-response cycle.
Generated QR codes are stored temporarily and served to the user.

Analytics
Basic analytics are implemented using SQLAlchemy queries:

We create a ClickEvent model to store information about each click (timestamp, referrer, user agent, etc.).
We use SQLAlchemy's aggregation functions to generate reports on click counts, popular times, and top referrers.

Link History
Link history is implemented with pagination for efficiency:

We add a user_id field to the URL model to associate URLs with users.
We implement a paginated API endpoint that returns a user's link history.
We use SQLAlchemy's limit() and offset() methods to implement pagination.

Caching
We use Redis as a caching layer to improve performance:

Short code to URL mappings are cached in Redis for fast retrieval.
We implement a cache invalidation strategy to ensure data consistency when URLs are updated or deleted.

Rate Limiting
Rate limiting is implemented using FastAPI middleware:

We track request counts per IP address using Redis.
We implement a sliding window rate limit algorithm.
When a user exceeds the rate limit, we return a 429 Too Many Requests response.

Project Structure
Copyscissor/
├── alembic/
│   └── versions/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   └── dependencies.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── url.py
│   │   └── click_event.py
│   ├── schemas/
│   │   └── url.py
│   ├── services/
│   │   ├── url_service.py
│   │   └── analytics_service.py
│   └── main.py
├── tests/
│   ├── api/
│   ├── services/
│   └── conftest.py
├── .env
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
Setup and Installation

Clone the repository:
Copygit clone https://github.com/yourusername/scissor.git
cd scissor

Set up a virtual environment:
Copypython -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

Install dependencies:
Copypip install -r requirements.txt

Set up environment variables:
Copycp .env.example .env
# Edit .env with your configuration

Initialize the database:
Copyalembic upgrade head

Start Redis:
Copyredis-server

Run the application:
Copyuvicorn app.main:app --reload


Usage
Here are some example API calls using curl:

Shorten a URL:
Copycurl -X POST "http://localhost:8000/shorten" -H "Content-Type: application/json" -d '{"url": "https://www.example.com/very/long/url"}'

Create a custom URL:
Copycurl -X POST "http://localhost:8000/custom" -H "Content-Type: application/json" -d '{"url": "https://www.example.com", "custom_path": "my-brand"}'

Get URL analytics:
Copycurl "http://localhost:8000/analytics/abc123"

Get user's link history:
Copycurl "http://localhost:8000/history?page=1&per_page=10" -H "Authorization: Bearer YOUR_ACCESS_TOKEN"


API Documentation
FastAPI provides built-in interactive API documentation. Once the application is running, you can access:

Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

These interfaces provide detailed information about each endpoint, including request/response schemas and the ability to try out the API directly from the browser.
Testing
We use pytest for unit and integration tests. To run the tests:
Copypytest
For a coverage report:
Copypytest --cov=app tests/
Key areas covered by tests include:

URL shortening and expansion
Custom URL creation
QR code generation
Analytics tracking
Rate limiting
Caching mechanisms

Performance Considerations

Caching: We use Redis to cache frequently accessed URLs, reducing database load.
Asynchronous Operations: FastAPI's asynchronous nature allows for efficient handling of concurrent requests.
Database Indexing: We create appropriate indexes on the URL and ClickEvent tables to speed up queries.
Pagination: Link history and analytics results are paginated to handle large datasets efficiently.

Security Considerations

Input Validation: All user inputs are validated using Pydantic models.
Rate Limiting: Prevents abuse of the API.
HTTPS: In production, all traffic should be served over HTTPS.
Authentication: Implement JWT authentication for user-specific features.
SQL Injection Prevention: Use of SQLAlchemy ORM and parametrized queries prevents SQL injection.
