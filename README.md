# Market Cycle Detection Service

A Dockerized service that analyzes economic indicators to detect market cycle phases and provides investment guidance based on current market conditions.

## Overview

This service combines multiple economic indicators from FRED (Federal Reserve Economic Data) and Yahoo Finance to create a composite market cycle indicator. It classifies market conditions into four phases:

- **Early**: Nascent expansion phase
- **Mid-Late**: Peak growth phase  
- **Decline**: Contraction phase
- **Uncertain**: Conflicting signals

## Features

### 📊 Economic Indicators Analyzed
- **Growth/Activity**: Leading Economic Index, Manufacturing/Services PMI, Capacity Utilization
- **Inflation**: Core CPI, Core PCE, Hourly Wages, PPI, Commodities
- **Rates & Credit**: 10-Year Treasury, High-Yield OAS
- **Financial Stress**: St. Louis Fed Financial Stress Index

### 🎯 Market Cycle Detection
- Z-score normalization of indicators
- Composite indicator calculation
- Slope analysis for trend detection
- Phase classification with dead-zone handling
- S&P 500 YoY performance overlay

### 📈 Outputs
- Interactive matplotlib charts with phase color coding
- Current market phase interpretation
- Investment guidance based on cycle phase
- Historical analysis from 2000 to present

## Quick Start

### Prerequisites
- Docker installed and running
- Internet connection for data fetching
- FRED API key (free from [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html))

### Build and Run

```bash
# Build the Docker image
./build.sh

# Run the service with your FRED API key
docker run --rm -e FRED_API_KEY=your_api_key_here alpha5-finance/detect-market-cycles:latest

# Run with output directory mounted
docker run --rm -e FRED_API_KEY=your_api_key_here -v $(pwd)/outputs:/workspace/outputs alpha5-finance/detect-market-cycles:latest
```

### Test the Service

```bash
# Export your FRED API key, then run tests (test.sh requires FRED_API_KEY)
export FRED_API_KEY=your_api_key_here
./test.sh
```

For Docker Compose, copy `env.example` to `.env` and set `FRED_API_KEY` there before `docker compose up`.

## Configuration

### Parameters (in main.py)

```python
START, END = '2000-01-01', datetime.today().strftime('%Y-%m-%d')
FREQ = 'ME'           # Monthly end frequency
SLOPE_WINDOW = 3      # Look-back periods for slope calculation
SMOOTH_WINDOW = 2     # Moving average window for smoothing
```

### Phase Classification Thresholds

```python
comp_thr = 0.15       # Composite threshold
slope_thr = 0.005     # Slope threshold
```

## Usage Examples

### Basic Execution
```bash
docker run --rm -e FRED_API_KEY=your_api_key_here alpha5-finance/detect-market-cycles:latest
```

### Scheduled Execution
```bash
# Daily execution with timestamp
docker run --rm -e FRED_API_KEY=your_api_key_here --name market-cycles-$(date +%Y%m%d) alpha5-finance/detect-market-cycles:latest
```

### Development Mode
```bash
# Interactive shell for debugging
docker run --rm -it -e FRED_API_KEY=your_api_key_here alpha5-finance/detect-market-cycles:latest /bin/bash
```

### With Custom Output Directory
```bash
# Mount local directory for outputs
docker run --rm -e FRED_API_KEY=your_api_key_here -v /path/to/outputs:/workspace/outputs alpha5-finance/detect-market-cycles:latest
```

## Output Interpretation

### Phase Classifications

#### Early Phase
- **Indicators**: Composite < -0.15, Slope > 0.005
- **Guidance**: Selective exposure to cyclical sectors
- **Risk**: Moderate, with contained risks

#### Mid-Late Phase  
- **Indicators**: Composite > 0.15
- **Guidance**: Shift to high-quality equities and defensive sectors
- **Risk**: High, inflationary pressures and monetary tightening

#### Decline Phase
- **Indicators**: Composite < -0.15, Slope < -0.005
- **Guidance**: De-risk portfolios, increase fixed income and cash
- **Risk**: Very high, deteriorating risk sentiment

#### Uncertain Phase
- **Indicators**: |Composite| ≤ 0.15
- **Guidance**: Maintain balanced allocations, await clearer signals
- **Risk**: High volatility, conflicting signals

## Technical Details

### Data Sources
- **FRED API**: Economic indicators via fredapi (fred-py-api)
- **Yahoo Finance**: S&P 500 data via yfinance
- **Update Frequency**: Monthly (configurable)

### Data Processing
1. **Fetch**: Download data from FRED and Yahoo Finance
2. **Transform**: Apply YoY changes, 12-month deltas, and inversions
3. **Normalize**: Z-score standardization
4. **Composite**: Weighted average of normalized indicators
5. **Classify**: Phase detection using thresholds and smoothing

### Performance
- **Data Range**: 2000-present (24+ years)
- **Processing Time**: ~30-60 seconds
- **Memory Usage**: ~200-500MB
- **Output Size**: ~2-5MB (charts + data)

## Docker Image Details

### Base Image
- **Python**: 3.13
- **OS**: Debian-based
- **Timezone**: America/New_York

### Dependencies
- pandas >= 2.0.0
- numpy >= 1.24.0
- fredapi >= 0.5.0
- yfinance >= 0.2.0
- matplotlib >= 3.7.0

### Image Size
- **Base**: ~1.2GB
- **With Dependencies**: ~1.8GB
- **Optimized**: Could be reduced with multi-stage builds

## Monitoring and Logging

### Container Logs
```bash
# View container logs
docker logs <container_id>

# Follow logs in real-time
docker logs -f <container_id>
```

### Health Checks
The service includes built-in error handling for:
- Network connectivity issues
- Data source unavailability
- Missing data periods
- Calculation errors

## Troubleshooting

### Common Issues

#### Data Fetching Errors
```bash
# Check network connectivity
docker run --rm alpha5-finance/detect-market-cycles:latest python -c "import requests; print(requests.get('https://fred.stlouisfed.org').status_code)"
```

#### Memory Issues
```bash
# Run with memory limits
docker run --rm --memory=1g alpha5-finance/detect-market-cycles:latest
```

#### Permission Issues
```bash
# Run with proper user permissions
docker run --rm -u $(id -u):$(id -g) alpha5-finance/detect-market-cycles:latest
```

### Debug Mode
```bash
# Interactive debugging
docker run --rm -it alpha5-finance/detect-market-cycles:latest /bin/bash
python main.py
```

## Integration

### Kubernetes Deployment

First, create a secret for your FRED API key:
```bash
kubectl create secret generic fred-api-secret --from-literal=api-key=your_api_key_here
```

Then deploy using the provided YAML:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: market-cycle-detector
spec:
  replicas: 1
  selector:
    matchLabels:
      app: market-cycle-detector
  template:
    metadata:
      labels:
        app: market-cycle-detector
    spec:
      containers:
      - name: market-cycle-detector
        image: alpha5-finance/detect-market-cycles:latest
        env:
        - name: FRED_API_KEY
          valueFrom:
            secretKeyRef:
              name: fred-api-secret
              key: api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### Cron Job
```bash
# Daily execution at 6 AM
0 6 * * * docker run --rm --name market-cycles-$(date +\%Y\%m\%d) alpha5-finance/detect-market-cycles:latest
```

## Contributing

### Development Setup
1. Clone the repository
2. Build the Docker image: `./build.sh`
3. Run tests: `./test.sh`
4. Make modifications to `main.py`
5. Rebuild and test

### Code Structure
- `main.py`: Main analysis script
- `Dockerfile`: Container definition
- `requirements.txt`: Python dependencies
- `build.sh`: Build script
- `test.sh`: Test script

## License

This project is part of the Alpha5 Finance Trade System.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review container logs
3. Test with the provided test script
4. Contact the development team
