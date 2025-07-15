# Outlook Webhook Service

A FastAPI-based service that integrates with Microsoft Graph API to receive and process Outlook email notifications via webhooks.

## Features

- 📧 Receive real-time notifications for new emails
- 🔄 Automatic subscription management
- 🔒 Secure authentication with Microsoft Graph
- 🚀 Built with FastAPI for high performance
- 📊 Structured logging with Loguru

## Prerequisites

- Python 3.8+
- Microsoft Azure AD App Registration
- Azure AD Application with required API permissions

## Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your Azure AD credentials:
   ```env
   AZURE_CLIENT_ID=your_client_id
   AZURE_CLIENT_SECRET=your_client_secret
   AZURE_TENANT_ID=your_tenant_id
   AZURE_USER_ID=user@yourdomain.com  # The email to monitor
   ```

## Installation

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

## Running the Application

Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8008`

## API Endpoints

- `POST /api/subscriptions` - Create a new subscription
- `POST /outlook-notify` - Webhook endpoint for Microsoft Graph notifications
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
```

### Linting
```bash
flake8
```

## Production Deployment

For production, make sure to:
1. Set up HTTPS (required by Microsoft Graph)
2. Use environment variables for configuration
3. Configure proper logging
4. Set up monitoring and alerts

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
