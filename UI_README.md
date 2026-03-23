# Alpha5 Market Cycle Intelligence - UI Documentation

## Overview

The Market Cycle Intelligence dashboard provides a futuristic, professional interface for analyzing market cycles. Designed with hedge funds in mind, it features:

- **Real-time Market Cycle Analysis**: Live updates of market phase detection
- **Interactive Charts**: Dynamic visualization of composite indicators and S&P 500 performance
- **Economic Indicators Grid**: Comprehensive view of all economic indicators
- **Customizable Parameters**: Adjust analysis parameters on the fly
- **Auto-refresh**: Automatic data updates every 5 minutes

## Features

### 🎯 Current Market Phase Indicator
- Large, color-coded phase ring showing current market phase
- Real-time composite score, slope, and S&P 500 YoY metrics
- Detailed interpretation of current market conditions

### 📊 Interactive Chart
- Composite Z-Score visualization with phase color coding
- S&P 500 YoY overlay
- Multiple view modes (Composite, S&P 500, Both)
- Time-based navigation with zoom capabilities

### 📈 Economic Indicators
- Filterable grid of all economic indicators
- Categories: Growth, Inflation, Rates & Credit
- Trend indicators showing direction and magnitude
- Real-time value updates

### ⚙️ Analysis Parameters
- Customizable date ranges
- Frequency selection (Daily, Weekly, Monthly, Quarterly)
- Slope and smoothing window adjustments
- One-click analysis execution

## Accessing the UI

### Local Development
1. Start the FastAPI server:
```bash
cd detect-market-cycles
uvicorn app:app --host 0.0.0.0 --port 8000
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

### Docker Deployment
The UI is automatically served when running the container:
```bash
docker-compose up market-cycle-api
```

Then access at:
```
http://localhost:8000
```

## UI Components

### Header
- **Logo**: Alpha5 branding with animated icon
- **Status Indicator**: Live status with pulse animation
- **Last Update**: Timestamp of most recent data refresh

### Phase Card
Displays the current market phase with:
- Visual phase indicator ring (color-coded)
- Phase label (Early, Mid-Late, Decline, Uncertain)
- Key metrics (Composite Score, Slope, S&P 500 YoY)
- Detailed interpretation text

### Chart Card
Interactive time-series chart showing:
- Market cycle composite indicator
- S&P 500 YoY performance
- Phase background colors
- Tooltips with detailed information

### Indicators Grid
Grid layout showing all economic indicators:
- Indicator name
- Current value
- Trend direction (up/down arrow)
- Category-based filtering

### Parameters Card
Control panel for analysis customization:
- Date range pickers
- Frequency dropdown
- Numeric inputs for slope and smoothing windows
- Run Analysis button

## Color Scheme

### Phase Colors
- **Early**: Green (#10b981) - Expansion phase
- **Mid-Late**: Blue (#3b82f6) - Peak growth phase
- **Decline**: Red (#ef4444) - Contraction phase
- **Uncertain**: Yellow (#f59e0b) - Conflicting signals

### Accent Colors
- **Primary**: Cyan (#00d4ff) - Main accent
- **Secondary**: Purple (#7c3aed) - Secondary accent
- **Success**: Green (#10b981) - Positive indicators
- **Danger**: Red (#ef4444) - Negative indicators

## Keyboard Shortcuts

- **R**: Refresh data
- **A**: Run analysis
- **Esc**: Close modals/overlays

## Browser Compatibility

- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

## Performance

- **Initial Load**: < 2 seconds
- **Data Refresh**: < 3 seconds
- **Chart Rendering**: < 1 second
- **Auto-refresh Interval**: 5 minutes

## Troubleshooting

### UI Not Loading
1. Check that the static files are in the `static/` directory
2. Verify FastAPI is running and accessible
3. Check browser console for JavaScript errors

### Charts Not Displaying
1. Ensure Chart.js CDN is accessible
2. Check that API is returning valid data
3. Verify date format in API response

### Data Not Updating
1. Check API endpoint connectivity
2. Verify FRED API key is configured
3. Check browser network tab for API errors

## API Integration

The UI communicates with the FastAPI backend via:
- `GET /analyze` - Fetch analysis results
- `GET /health` - Health check
- `GET /status` - Service status

All API calls are made via JavaScript Fetch API with proper error handling.

## Customization

### Changing Colors
Edit `static/css/style.css` and modify CSS variables:
```css
:root {
    --accent-primary: #00d4ff;
    --phase-early: #10b981;
    /* ... */
}
```

### Adjusting Auto-refresh
Edit `static/js/app.js`:
```javascript
startAutoRefresh() {
    // Change interval (in milliseconds)
    this.autoRefreshInterval = setInterval(() => {
        this.loadInitialData();
    }, 5 * 60 * 1000); // 5 minutes
}
```

### Adding New Indicators
The indicators are automatically populated from the API response. To add custom indicators, modify the `updateIndicators()` method in `app.js`.

## Security Notes

- CORS is currently set to allow all origins (change in production)
- No authentication is implemented (add as needed)
- API keys should be kept secure and not exposed in frontend code

## Future Enhancements

Potential improvements:
- WebSocket support for real-time updates
- Export functionality (PDF, CSV)
- Historical comparison views
- Custom alert thresholds
- Multi-timeframe analysis
- Dark/Light theme toggle

