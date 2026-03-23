# Market Cycle Detection API Service

This API service allows you to run market cycle analysis remotely and retrieve results via HTTP endpoints.

## Quick Start

### Start the API Service

```bash
docker-compose up -d market-cycle-api
```

The API will be available at `http://localhost:8000`

### Access the API

- **Interactive Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Documentation**: http://localhost:8000/redoc (ReDoc)
- **Root Page**: http://localhost:8000

## API Endpoints

### Health Check
```bash
GET /health
```

Returns service health status.

### Service Status
```bash
GET /status
```

Returns service information and available endpoints.

### Run Analysis (GET)
```bash
GET /analyze?start_date=2023-01-01&end_date=2024-12-31&generate_plot=true
```

**Query Parameters:**
- `start_date` (optional): Start date in YYYY-MM-DD format (default: 365 days ago)
- `end_date` (optional): End date in YYYY-MM-DD format (default: today)
- `freq` (optional): Pandas resample frequency (default: 'ME' for month-end)
- `slope_window` (optional): Look-back periods for slope calculation (default: 3)
- `smooth_window` (optional): Window for composite moving average (default: 2)
- `save_to_db` (optional): Whether to save results to database (default: true)
- `generate_plot` (optional): Whether to generate plot image (default: false)

### Run Analysis (POST)
```bash
POST /analyze
Content-Type: application/json

{
  "start_date": "2023-01-01",
  "end_date": "2024-12-31",
  "freq": "ME",
  "slope_window": 3,
  "smooth_window": 2,
  "save_to_db": true,
  "generate_plot": false
}
```

## Example Usage

### Using cURL

```bash
# Simple analysis
curl http://localhost:8000/analyze

# Analysis with custom date range
curl "http://localhost:8000/analyze?start_date=2023-01-01&end_date=2024-12-31"

# Analysis with plot generation
curl "http://localhost:8000/analyze?generate_plot=true" > result.json
```

### Using Python

```python
import requests

# Run analysis
response = requests.get("http://localhost:8000/analyze", params={
    "start_date": "2023-01-01",
    "end_date": "2024-12-31",
    "generate_plot": True
})

result = response.json()
print(f"Current Phase: {result['current_phase']}")
print(f"Interpretation: {result['interpretation']}")

# If plot was generated, it's in base64 format
if result.get('plot'):
    import base64
    plot_data = base64.b64decode(result['plot'])
    with open('market_cycle_plot.png', 'wb') as f:
        f.write(plot_data)
```

### Using JavaScript/Fetch

```javascript
// Run analysis
fetch('http://localhost:8000/analyze?generate_plot=true')
  .then(response => response.json())
  .then(data => {
    console.log('Current Phase:', data.current_phase);
    console.log('Interpretation:', data.interpretation);
    
    // Display plot if generated
    if (data.plot) {
      const img = document.createElement('img');
      img.src = 'data:image/png;base64,' + data.plot;
      document.body.appendChild(img);
    }
  });
```

## Response Format

The API returns a JSON object with the following structure:

```json
{
  "status": "success",
  "analysis_date": "2024-12-31",
  "current_phase": "Early",
  "current_composite": 0.25,
  "current_slope": 0.01,
  "current_sp500_yoy": 15.5,
  "interpretation": "As of 2024-12-31, the composite is 0.25...",
  "parameters": {
    "start_date": "2023-01-01",
    "end_date": "2024-12-31",
    "freq": "ME",
    "slope_window": 3,
    "smooth_window": 2
  },
  "data": {
    "composite_scores": {
      "dates": ["2023-01-31", "2023-02-28", ...],
      "composite": [0.1, 0.2, ...],
      "composite_smoothed": [0.15, 0.25, ...],
      "slope": [0.01, 0.02, ...],
      "phases": ["Early", "Mid-Late", ...]
    },
    "sp500_yoy": {
      "dates": ["2023-01-31", ...],
      "values": [10.5, 12.3, ...]
    },
    "raw_series": {...},
    "transformed_series": {...}
  },
  "plot": "base64_encoded_image_string_if_generate_plot=true"
}
```

## Docker Compose

The API service is configured in `docker-compose.yml`:

```yaml
market-cycle-api:
  ports:
    - "8000:8000"
  command: uvicorn app:app --host 0.0.0.0 --port 8000
```

To change the port, modify the port mapping in docker-compose.yml.

## Environment Variables

The API service uses the same environment variables as the main script:

- `FRED_API_KEY`: FRED API key (required for FRED data)
- `DB_HOST`: PostgreSQL host (default: localhost)
- `DB_PORT`: PostgreSQL port (default: 5432)
- `DB_NAME`: Database name (default: postgres)
- `DB_USER`: Database user (default: postgres)
- `DB_PASSWORD`: Database password (unset by default; set for your environment)

Copy `env.example` to `.env`, fill in values, and keep `.env` out of version control.

## Notes

- The API service automatically saves results to PostgreSQL if `save_to_db=true`
- Plot generation adds processing time but provides visual output
- The service includes CORS middleware for cross-origin requests
- Health checks are configured for container orchestration

