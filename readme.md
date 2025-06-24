
<pre><code>## 📁 Project Structure

<details>
<summary>Click to expand</summary>

```text
travel_ai_agent/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application entry point
│   ├── config.py             # Configuration management
│   ├── database.py           # Database connection and models
│   ├── models/
│   │   ├── __init__.py
│   │   ├── email_models.py       # Email-related data models
│   │   ├── travel_models.py      # Travel inquiry data models
│   │   └── database_models.py    # SQLAlchemy database models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── email_service.py      # Email integration (Gmail/Outlook)
│   │   ├── ai_service.py         # LangChain AI processing
│   │   ├── excel_service.py      # Excel generation
│   │   └── thread_service.py     # Conversation thread management
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py         # Celery configuration
│   │   └── email_worker.py       # Celery tasks for email processing
│   ├── api/
│   │   ├── __init__.py
│   │   ├── email_routes.py       # Email-related API endpoints
│   │   └── health_routes.py      # Health check endpoints
│   └── utils/
│       ├── __init__.py
│       ├── validators.py         # Data validation utilities
│       ├── logger.py             # Logging configuration
│       └── exceptions.py         # Custom exceptions
├── templates/
│   └── travel_quote_template.xlsx
├── tests/
│   ├── __init__.py
│   ├── test_email_service.py
│   ├── test_ai_service.py
│   └── test_excel_service.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
├── scripts/
│   ├── setup_db.py
│   └── run_tests.py
├── requirements.txt
├── .env.example
├── README.md
└── alembic/
    ├── versions/
    └── alembic.ini
```

</details>
</code></pre>
