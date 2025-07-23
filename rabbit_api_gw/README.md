# RabbitMQ Queue Manager

Express service for managing RabbitMQ queues and handling page view data distribution.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file based on `.env.example` and configure your environment variables.

3. Start the service:
```bash
npm start
```

For development with auto-reload:
```bash
npm run dev
```

## API Endpoints

### Submit Single Page View
- **POST** `/pageviews/single`
- **Body:**
```json
{
  "page": "example.html",
  "timestamp": "2025-06-01_21:00"
}
```
- **Response:** 201 Created
```json
{
  "message": "Page view data published successfully",
  "queue": "page_views2",
  "data": {
    "example.html": {
      "2025-06-01_21:00": 1
    }
  }
}
```

### Submit Multiple Page Views
- **POST** `/pageviews/multi`
- **Body:**
```json
{
  "altman.html": {
    "2025-06-01_21:00": 103,
    "2025-06-01_22:00": 200,
    "2025-06-01_23:00": 405
  },
  "musk.html": {
    "2025-06-01_21:00": 838,
    "2025-06-01_22:00": 654
  }
}
```
- **Response:** 201 Created
```json
{
  "message": "Multiple page views data published successfully",
  "queue": "page_views1",
  "data": { ... }
}
```

The service automatically distributes incoming page view data across four queues (`page_views1` through `page_views4`) using random even distribution.
