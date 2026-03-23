"""
FastAPI application for Market Cycle Detection Service
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
import analyzer
from datetime import datetime, timedelta
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Market Cycle Detection API",
    description="API service for running market cycle analysis and retrieving results",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


class AnalysisRequest(BaseModel):
    """Request model for analysis parameters"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    freq: Optional[str] = "ME"
    slope_window: Optional[int] = 3
    smooth_window: Optional[int] = 2
    save_to_db: Optional[bool] = True
    generate_plot: Optional[bool] = False


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - serves the main dashboard UI"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        # Fallback to simple HTML if static files not found
        return """
        <html>
            <head>
                <title>Market Cycle Detection API</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: #fff; }
                    h1 { color: #4CAF50; }
                    a { color: #4CAF50; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                    .endpoint { background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 5px; }
                    code { background: #3a3a3a; padding: 2px 6px; border-radius: 3px; }
                </style>
            </head>
            <body>
                <h1>Market Cycle Detection API</h1>
                <p>Welcome to the Market Cycle Detection API service.</p>
                <p><a href="/docs">📚 Interactive API Documentation (Swagger UI)</a></p>
                <p><a href="/redoc">📖 Alternative API Documentation (ReDoc)</a></p>
                <h2>Available Endpoints:</h2>
                <div class="endpoint">
                    <strong>GET /health</strong> - Health check endpoint
                </div>
                <div class="endpoint">
                    <strong>POST /analyze</strong> - Run market cycle analysis
                </div>
                <div class="endpoint">
                    <strong>GET /analyze</strong> - Run analysis with query parameters
                </div>
                <div class="endpoint">
                    <strong>GET /status</strong> - Get service status
                </div>
            </body>
        </html>
        """


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "market-cycle-detection",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/status")
async def status():
    """Get service status and information"""
    return {
        "status": "running",
        "service": "market-cycle-detection",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "analyze_post": "/analyze (POST)",
            "analyze_get": "/analyze (GET)",
            "docs": "/docs"
        }
    }


@app.post("/analyze")
async def analyze_post(request: AnalysisRequest):
    """
    Run market cycle analysis with POST request
    
    Accepts JSON body with analysis parameters:
    - start_date: Start date in YYYY-MM-DD format (optional)
    - end_date: End date in YYYY-MM-DD format (optional)
    - freq: Pandas resample frequency (default: 'ME')
    - slope_window: Look-back periods for slope (default: 3)
    - smooth_window: Window for moving average (default: 2)
    - save_to_db: Whether to save to database (default: True)
    - generate_plot: Whether to generate plot (default: False)
    """
    try:
        logger.info(f"Running analysis with parameters: {request.dict()}")
        results = analyzer.run_analysis(
            start_date=request.start_date,
            end_date=request.end_date,
            freq=request.freq,
            slope_window=request.slope_window,
            smooth_window=request.smooth_window,
            save_to_db=request.save_to_db,
            generate_plots=request.generate_plot
        )
        return JSONResponse(content=results)
    except Exception as e:
        logger.error(f"Error running analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/analyze")
async def analyze_get(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    freq: str = Query("ME", description="Pandas resample frequency"),
    slope_window: int = Query(3, description="Look-back periods for slope calculation"),
    smooth_window: int = Query(2, description="Window for composite moving average"),
    save_to_db: bool = Query(True, description="Whether to save results to database"),
    generate_plot: bool = Query(False, description="Whether to generate plot image")
):
    """
    Run market cycle analysis with GET request
    
    Query parameters:
    - start_date: Start date in YYYY-MM-DD format (optional)
    - end_date: End date in YYYY-MM-DD format (optional)
    - freq: Pandas resample frequency (default: 'ME')
    - slope_window: Look-back periods for slope (default: 3)
    - smooth_window: Window for moving average (default: 2)
    - save_to_db: Whether to save to database (default: True)
    - generate_plot: Whether to generate plot (default: False)
    """
    try:
        logger.info(f"Running analysis with GET parameters: start_date={start_date}, end_date={end_date}")
        results = analyzer.run_analysis(
            start_date=start_date,
            end_date=end_date,
            freq=freq,
            slope_window=slope_window,
            smooth_window=smooth_window,
            save_to_db=save_to_db,
            generate_plots=generate_plot
        )
        return JSONResponse(content=results)
    except Exception as e:
        logger.error(f"Error running analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

