# Sudan News API

The consumer/web API component of the Sudanese News Aggregator system. This service provides REST endpoints and web interface for accessing clustered news events.

## Features

- **REST API**: Complete REST API for mobile apps and integrations
- **Web Interface**: Responsive Arabic web interface with RTL support
- **Real-time Search**: Dynamic search and filtering capabilities
- **Pagination**: Efficient pagination for large datasets
- **Caching**: HTTP caching headers for improved performance
- **CORS Support**: Cross-origin resource sharing for web clients
- **Health Checks**: Monitoring endpoints for deployment

## Architecture

```
Web/Mobile Clients → Flask API → Repositories → Database
```

## Installation

### Prerequisites
- Python 3.11+
- Access to shared_models package

### Setup

1. **Navigate to API directory**:
   ```bash
   cd sudan-news-api
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database URL
   ```

4. **Initialize database** (if not already done):
   ```bash
   cd ../shared_models
   alembic upgrade head
   cd ../sudan-news-api
   ```

## Usage

### Development Server

```bash
# Using Flask development server
flask run

# Or using Python directly
python src/app.py
```

The API will be available at `http://localhost:5000`

### Production Server

```bash
# Using Gunicorn
gunicorn --config gunicorn.conf.py src.app:app

# Or using the provided script
./start.sh
```

## API Endpoints

### Clusters

**GET /api/clusters**
- Get paginated list of event clusters
- Query parameters: `page`, `limit`, `q` (search), `category`, `has_entities`
- Response: Array of cluster summaries with mobile-friendly format

**GET /api/cluster/{id}**
- Get detailed information about a specific cluster
- Response: Complete cluster data with all articles and entities

### Categories

**GET /api/categories**
- Get available news categories
- Response: Array of category names

### Articles

**GET /api/articles**
- Get articles with filtering options
- Query parameters: `date_from`, `date_to`, `keyword`
- Response: Array of article objects

### Push Notifications

**POST /api/register_token**
- Register device for push notifications
- Body: `{"user_id": "optional", "device_id": "required", "token": "required", "platform": "android|ios"}`
- Response: Success confirmation

### Push Notifications

**POST /api/send_notification**
- Send custom push notification to all users
- Body: `{"title": "required", "body": "required", "data": {"key": "value"}}`
- Response: `{"success": 5, "failure": 0}`

**POST /api/notify_new_cluster/{cluster_id}**
- Send notification for a new cluster
- Response: Notification result with success/failure counts

**POST /api/notify_popular_clusters**
- Send notifications for clusters with many sources (≥10 by default)
- Response: Results for each popular cluster notified

**GET /api/notification_stats**
- Get notification statistics and popular clusters info
- Response: Token stats, popular clusters count, Firebase status

### Health Check

**GET /health**
- Service health check endpoint
- Response: `{"status": "healthy", "service": "sudan-news-api"}`

## Web Interface

**GET /**
- Main web interface with cluster listings
- Features: Search, filtering, infinite scroll, responsive design

**GET /event/{id}**
- Detailed view of a specific news event
- Shows all articles in the cluster with bias ratings

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///news_aggregator.db` |
| `FLASK_ENV` | Flask environment | `development` |
| `SECRET_KEY` | Flask secret key | Required for production |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Gunicorn Configuration

The `gunicorn.conf.py` file contains production server settings:
- 4 worker processes
- Request timeout: 30 seconds
- Access and error logging
- Process management

## Docker Deployment

### Build Image
```bash
docker build -t sudan-news-api .
```

### Run Container
```bash
docker run -p 8000:8000 --env-file .env sudan-news-api
```

### Docker Compose Example
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## API Response Formats

### Cluster Summary (Mobile API)
```json
{
  "id": 123,
  "headline": "Event title",
  "description": "First article description",
  "image_url": "https://...",
  "country_city": "Sudan/Khartoum",
  "first_date_of_publication": "2025-01-15T10:30:00",
  "number_of_sources": 5
}
```

### Cluster Details
```json
{
  "id": 123,
  "title": "Event title",
  "number_of_sources": 5,
  "published_at": "2025-01-15T10:30:00",
  "created_at": "2025-01-15T10:30:00",
  "articles": [
    {
      "id": 456,
      "headline": "Article headline",
      "description": "Article content",
      "published_at": "2025-01-15T10:30:00",
      "article_url": "https://...",
      "image_url": "https://...",
      "source_name": "Source Name",
      "bias": "Neutral",
      "entities": {
        "people": ["Person A"],
        "cities": ["Khartoum"],
        "nlp_category": "سياسة"
      }
    }
  ]
}
```

## Caching Strategy

- **Cluster listings**: 5-minute cache (`max-age=300`)
- **Cluster details**: 10-minute cache (`max-age=600`)
- **Categories**: 1-hour cache (`max-age=3600`)
- **ETags**: Automatic ETag generation for conditional requests

## Error Handling

- **400 Bad Request**: Invalid request parameters
- **404 Not Found**: Cluster/article not found
- **500 Internal Server Error**: Server errors (logged)

## Monitoring

Monitor API health through:
- `/health` endpoint responses
- Gunicorn access/error logs
- Database connection status
- Response time metrics

## Security

- Input validation on all endpoints
- SQL injection prevention via SQLAlchemy
- CORS configuration for web clients
- No sensitive data in logs
- Environment variable configuration

## Performance

- **Database**: Connection pooling via SQLAlchemy
- **Caching**: HTTP caching headers
- **Pagination**: Efficient offset-based pagination
- **Gzip**: Automatic response compression

## Development

### Testing API Endpoints

```bash
# Get clusters
curl "http://localhost:5000/api/clusters?page=1&limit=10"

# Get cluster details
curl "http://localhost:5000/api/cluster/123"

# Register push token
curl -X POST "http://localhost:5000/api/register_token" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "token": "test", "platform": "android"}'
```

### Debugging

Set `LOG_LEVEL=DEBUG` for detailed request/response logging.

## Troubleshooting

### Common Issues

**Database connection failed**: Check `DATABASE_URL` in `.env`

**Template not found**: Ensure `templates/` and `static/` directories are copied

**CORS errors**: Configure `CORS_ORIGINS` appropriately

**Memory usage**: Monitor Gunicorn worker processes

**Slow responses**: Check database indexes and query performance

### Logs

Check logs in:
- `access.log` (Gunicorn access log)
- `error.log` (Gunicorn error log)
- Console output (development mode)
