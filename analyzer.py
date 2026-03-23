"""
Market Cycle Analysis Module
Contains the core analysis logic extracted from main.py
"""

import pandas as pd
import numpy as np
from fredapi import Fred
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from datetime import datetime, timedelta
import matplotlib.dates as mdates
import math
import os
import logging
import db_utils
from typing import Dict, Any, Optional
import base64
import io

logger = logging.getLogger(__name__)


def clean_for_json(value):
    """
    Clean a value to be JSON-compliant by replacing infinity and NaN with None.
    
    Args:
        value: The value to clean (can be scalar, Series, or array-like)
    
    Returns:
        Cleaned value that is JSON-serializable
    """
    if isinstance(value, pd.Series):
        # Replace infinity and NaN with None for Series
        cleaned = value.copy()
        # Replace infinity values with np.nan first, then we'll convert all NaN to None
        cleaned = cleaned.replace([np.inf, -np.inf], np.nan)
        # Convert to list and clean each value
        result = []
        for x in cleaned:
            if pd.isna(x):
                result.append(None)
            elif isinstance(x, (float, np.floating)):
                if math.isinf(x) or math.isnan(x):
                    result.append(None)
                else:
                    result.append(float(x))
            elif isinstance(x, (int, np.integer)):
                result.append(int(x))
            else:
                result.append(x)
        return result
    elif isinstance(value, pd.DataFrame):
        # Handle DataFrame by converting to dict
        cleaned = value.replace([np.inf, -np.inf], np.nan)
        # Convert to dict and clean each column
        result_dict = {}
        for col in cleaned.columns:
            result_dict[col] = clean_for_json(cleaned[col])
        return result_dict
    elif isinstance(value, (list, tuple)):
        # Recursively clean list items
        return [clean_for_json(item) for item in value]
    elif isinstance(value, (np.integer, np.floating)):
        # Handle numpy numeric types
        if np.isinf(value) or np.isnan(value):
            return None
        return float(value) if isinstance(value, np.floating) else int(value)
    elif isinstance(value, float):
        # Handle Python float (check for infinity and NaN)
        if math.isinf(value) or math.isnan(value):
            return None
        return value
    elif isinstance(value, dict):
        # Recursively clean dictionary values
        return {k: clean_for_json(v) for k, v in value.items()}
    else:
        return value

# SERIES MAP
FRED_MAP = {
    # growth / activity
    'LEI': 'USSLIND',  # Leading Index for US (Philly Fed state leading), proxy for overall LEI
    'Philly Manuf Diff': 'GACDFSA066MSFRBPHI',  # Philly Fed manufacturing diffusion index, proxy for ISM Mfg PMI
    'Texas Serv Diff': 'TSSOSBACTUAMFRBDAL',  # Dallas Fed services diffusion index, proxy for ISM Services PMI
    'Capacity Util': 'CUMFNS',  # Industrial capacity utilization rate
    'BBK Leading': 'BBKMLEIX',  # Brave‑Butters‑Kelley leading index, leading growth component
    'CFNAI 3MMA': 'CFNAIMA3',  # Chicago Fed National Financial Activity Index 3‑mo avg

    # inflation sub‑block
    'Core CPI': 'CPILFESL',  # Core CPI ex‑food & energy, inflation proxy
    'Core PCE': 'PCEPILFE',  # Core PCE inflation proxy
    'Hourly Wage': 'CES0500000003',  # Avg hourly earnings YoY (BLS)
    'PPI': 'PPIACO',  # Producer Price Index commodities YoY
    'Commodities': 'PALLFNFINDEXM',  # BCOM commodity price index YoY

    # rates & credit
    '10Y': 'DGS10',  # 10‑year Treasury yield (Δ12m)
    'HY OAS': 'BAMLH0A0HYM2',  # High‑yield OAS (Δ12m, inverted)

    # stress proxy
    'StLouis FSI': 'STLFSI4',  # St. Louis Fed Financial Stress Index (inverted)
}


def run_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    freq: str = 'ME',
    slope_window: int = 3,
    smooth_window: int = 2,
    save_to_db: bool = True,
    generate_plots: bool = False
) -> Dict[str, Any]:
    """
    Run market cycle analysis and return results
    
    Args:
        start_date: Start date in YYYY-MM-DD format (default: 365 days ago)
        end_date: End date in YYYY-MM-DD format (default: today)
        freq: Pandas resample frequency (default: 'ME' for month-end)
        slope_window: Look-back periods for slope calculation (default: 3)
        smooth_window: Window for composite moving average (default: 2)
        save_to_db: Whether to save results to database (default: True)
        generate_plots: Whether to generate matplotlib plots (default: False)
    
    Returns:
        Dictionary containing analysis results
    """
    # Set default dates if not provided
    if start_date is None:
        start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    
    # Initialize FRED API client
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        raise ValueError(
            'FRED_API_KEY is not set. Add it to your environment or .env file. '
            'See https://fred.stlouisfed.org/docs/api/api_key.html'
        )
    fred = Fred(api_key=fred_api_key)
    
    # Initialize database tables if saving to DB
    if save_to_db:
        try:
            db_utils.ensure_tables_exist()
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize database tables: {e}. Continuing without database storage.")
            save_to_db = False
    
    # FETCH & RESAMPLE
    raw = {}
    for k, tkr in FRED_MAP.items():
        try:
            data = fred.get_series(tkr, start=start_date, end=end_date)
            raw[k] = data
        except Exception as e:
            logger.warning(f"Could not fetch {k} ({tkr}): {e}")
            raw[k] = pd.Series(dtype=float)
    
    df = pd.DataFrame(raw).resample(freq).last().ffill()
    
    # Save raw data to database
    if save_to_db:
        try:
            db_utils.save_raw_data(df)
        except Exception as e:
            logger.warning(f"Failed to save raw data to database: {e}")
    
    df_raw = df.copy()
    
    # TRANSFORMS
    yoy = lambda s: s.pct_change(12) * 100
    delta12 = lambda s: s.diff(12)
    invert = lambda s: -s
    
    df['LEI'] = yoy(df['LEI'])
    df['Capacity Util'] = yoy(df['Capacity Util'])
    df['BBK Leading'] = yoy(df['BBK Leading'])
    for c in ['Core CPI', 'Core PCE', 'Hourly Wage', 'PPI', 'Commodities']:
        df[c] = yoy(df[c])
    df['10Y'] = invert(delta12(df['10Y']))
    df['HY OAS'] = invert(delta12(df['HY OAS']))
    df['StLouis FSI'] = invert(df['StLouis FSI'])
    
    # INFLATION COMPOSITE
    infl_cols = ['Core CPI', 'Core PCE', 'Hourly Wage', 'PPI', 'Commodities']
    df['Inflation'] = df[infl_cols].mean(axis=1)
    
    # Save transformed data to database
    if save_to_db:
        try:
            db_utils.save_transformed_data(df)
        except Exception as e:
            logger.warning(f"Failed to save transformed data to database: {e}")
    
    # FINAL INPUT LIST
    inputs = [
        'LEI', 'Philly Manuf Diff', 'Texas Serv Diff',
        'Capacity Util', 'BBK Leading', 'CFNAI 3MMA',
        'Inflation', '10Y', 'HY OAS', 'StLouis FSI'
    ]
    
    # Z-SCORES & COMPOSITE
    # Clean data before z-score calculation to avoid warnings
    df_clean = df[inputs].replace([np.inf, -np.inf], np.nan)
    
    # Calculate z-scores with proper handling of invalid values
    def safe_zscore(series):
        """Calculate z-score with handling for invalid values"""
        # Replace inf with nan
        clean_series = series.replace([np.inf, -np.inf], np.nan)
        # Calculate mean and std, ignoring NaN values
        mean_val = clean_series.mean()
        std_val = clean_series.std()
        
        # Handle division by zero (constant series)
        if std_val == 0 or pd.isna(std_val) or pd.isna(mean_val):
            return pd.Series([0.0] * len(clean_series), index=clean_series.index)
        
        # Calculate z-score
        z_vals = (clean_series - mean_val) / std_val
        # Replace any resulting inf/nan with 0
        z_vals = z_vals.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        return z_vals
    
    # Suppress warnings during z-score calculation
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=RuntimeWarning)
        z = df_clean.apply(safe_zscore)
    
    comp = z.mean(axis=1)
    comp_sm = comp.rolling(smooth_window, min_periods=1).mean()
    slope = comp.diff(slope_window)
    
    # PHASE CLASSIFICATION w/ DEAD‑ZONE
    comp_thr, slope_thr = 0.15, 0.005
    cond_early = (comp < -comp_thr) & (slope > slope_thr)
    cond_midlate = comp > comp_thr
    cond_decline = (comp < -comp_thr) & (slope < -slope_thr)
    cond_unc = comp.abs() <= comp_thr
    
    # initial labels as a Series
    phase = pd.Series('Mid-Late', index=comp.index)
    phase[cond_early] = 'Early'
    phase[cond_decline] = 'Decline'
    phase[cond_unc] = 'Uncertain'
    
    # map to integer codes
    code_map = {'Early': 0, 'Mid-Late': 1, 'Decline': 2, 'Uncertain': 3}
    inv_map = {v: k for k, v in code_map.items()}
    codes = phase.map(code_map)
    
    # apply centered rolling‑mode
    min_run = 6
    smoothed_codes = codes.rolling(
        window=min_run, center=True, min_periods=1
    ).apply(
        lambda x: pd.Series(x).value_counts().idxmax(),
        raw=False
    )
    
    # back to labels
    phase = smoothed_codes.round().astype(int).map(inv_map).values
    
    # Convert phase back to Series for database storage
    phase_series = pd.Series(phase, index=comp.index)
    
    # Save composite data to database
    if save_to_db:
        try:
            db_utils.save_composite_data(comp, comp_sm, slope, phase_series)
        except Exception as e:
            logger.warning(f"Failed to save composite data to database: {e}")
    
    # S&P 500 YoY % via yfinance
    try:
        data = yf.download('^GSPC',
                          start=start_date,
                          end=end_date,
                          auto_adjust=False,
                          progress=False)
        data.columns = data.columns.get_level_values(0)
        spx = data['Adj Close'].resample(freq).last().ffill()
        spx_yoy = spx.pct_change(12) * 100
    except Exception as e:
        logger.warning(f"Failed to fetch S&P 500 data: {e}")
        spx_yoy = pd.Series(dtype=float)
    
    # Save S&P 500 data to database
    if save_to_db and not spx_yoy.empty:
        try:
            db_utils.save_sp500_data(spx_yoy)
        except Exception as e:
            logger.warning(f"Failed to save S&P 500 data to database: {e}")
    
    # Get current phase information
    current_date = phase_series.index[-1]
    current_phase = phase_series.iloc[-1]
    current_comp = comp_sm.loc[current_date] if current_date in comp_sm.index else None
    current_slope = slope.loc[current_date] if current_date in slope.index else None
    current_spx_yoy = spx_yoy.loc[current_date] if not spx_yoy.empty and current_date in spx_yoy.index else None
    
    # Clean infinity and NaN values from current metrics
    if current_comp is not None:
        current_comp = clean_for_json(current_comp)
    if current_slope is not None:
        current_slope = clean_for_json(current_slope)
    if current_spx_yoy is not None:
        current_spx_yoy = clean_for_json(current_spx_yoy)
    
    # Generate interpretation
    interpretation = ""
    if current_phase == 'Early':
        interpretation = (
            f"As of {current_date.date()}, the composite is {current_comp:.2f} "
            f"(+{current_slope:.3f} over {slope_window}m) and S&P YoY is {current_spx_yoy:.1f}%. "
            "Early-phase conditions indicate nascent expansion. "
            "Leading activity indicators have bottomed and credit spreads are narrowing. "
            "Selective exposure to cyclical sectors may capture emerging growth while risks remain contained."
        )
    elif current_phase == 'Mid-Late':
        interpretation = (
            f"As of {current_date.date()}, the composite stands at {current_comp:.2f} "
            f"(slope {current_slope:.3f}) with S&P YoY {current_spx_yoy:.1f}%. "
            "Mid-to-late cycle signals peak growth. "
            "Inflationary pressures and monetary tightening typically intensify in this phase. "
            "Shift allocation toward high-quality equities and defensive sectors to protect gains."
        )
    elif current_phase == 'Decline':
        interpretation = (
            f"As of {current_date.date()}, the composite reads {current_comp:.2f} "
            f"(slope {current_slope:.3f}) and S&P YoY is {current_spx_yoy:.1f}%. "
            "Decline-phase patterns signal contraction. "
            "Risk sentiment deteriorates and liquidity tightens. "
            "Consider de-risking portfolios: increase fixed income, cash buffers, and low-volatility assets."
        )
    elif current_phase == 'Uncertain':
        interpretation = (
            f"As of {current_date.date()}, the composite is neutral at {current_comp:.2f} "
            f"(slope {current_slope:.3f}) with S&P YoY {current_spx_yoy:.1f}%. "
            "Signals conflict and volatility often rises. "
            "Maintain balanced allocations, await clearer directional cues, and manage risk with disciplined stops."
        )
    else:
        interpretation = "Phase classification unavailable."
    
    # Prepare results with cleaned data (replace infinity and NaN)
    results = {
        'status': 'success',
        'analysis_date': current_date.isoformat() if hasattr(current_date, 'isoformat') else str(current_date),
        'current_phase': current_phase,
        'current_composite': current_comp,
        'current_slope': current_slope,
        'current_sp500_yoy': current_spx_yoy,
        'interpretation': interpretation,
        'parameters': {
            'start_date': start_date,
            'end_date': end_date,
            'freq': freq,
            'slope_window': slope_window,
            'smooth_window': smooth_window
        },
        'data': {
            'composite_scores': {
                'dates': [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in comp.index],
                'composite': clean_for_json(comp),
                'composite_smoothed': clean_for_json(comp_sm),
                'slope': clean_for_json(slope),
                'phases': phase.tolist()
            },
            'sp500_yoy': {
                'dates': [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in spx_yoy.index] if not spx_yoy.empty else [],
                'values': clean_for_json(spx_yoy) if not spx_yoy.empty else []
            },
            'raw_series': {
                'dates': [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in df_raw.index],
                'series': {col: clean_for_json(df_raw[col]) for col in df_raw.columns}
            },
            'transformed_series': {
                'dates': [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in df.index],
                'series': {col: clean_for_json(df[col]) for col in df.columns}
            }
        }
    }
    
    # Generate plot if requested
    if generate_plots:
        try:
            plot_base64 = _generate_plot(comp_sm, phase, phase_series, spx_yoy, smooth_window)
            results['plot'] = plot_base64
        except Exception as e:
            logger.warning(f"Failed to generate plot: {e}")
            results['plot'] = None
    
    return results


def _generate_plot(comp_sm, phase, phase_series, spx_yoy, smooth_window):
    """Generate plot and return as base64 encoded string"""
    phase_colors = {
        'Early': '#54d62c',
        'Mid-Late': '#3fa1ff',
        'Decline': '#ff4c4c',
        'Uncertain': '#ffd400'
    }
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    mask = pd.Series(phase, index=comp_sm.index)
    grp = (mask != mask.shift()).cumsum()
    for ph, col in phase_colors.items():
        for _, span in mask[mask == ph].groupby(grp):
            ax.axvspan(span.index[0], span.index[-1],
                      color=col, alpha=0.20)
    
    ax.plot(comp_sm.index, comp_sm,
           lw=2, color='white',
           label=f'Cycle Composite ({smooth_window}-m MA)')
    ax.axhline(0, color='#777', lw=1)
    
    if not spx_yoy.empty:
        ax2 = ax.twinx()
        ax2.plot(spx_yoy.index, spx_yoy,
                lw=2, ls='--', color='#00d084',
                zorder=5,
                label='S&P 500 YoY %')
        ax2.set_ylabel('S&P 500 YoY %', color='#00d084')
        ax2.tick_params(axis='y', colors='#00d084')
        ax2.set_ylim(-80, 80)
    
    phase_patches = [Patch(facecolor=c, alpha=0.4, label=p)
                    for p, c in phase_colors.items()]
    leg1 = ax.legend(handles=phase_patches, title='Cycle Phase',
                    loc='upper right', ncol=3,
                    framealpha=0.3, fontsize=9)
    
    h1, l1 = ax.get_legend_handles_labels()
    if not spx_yoy.empty:
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2,
                 loc='upper left', framealpha=0.3,
                 fontsize=9)
    else:
        ax.legend(h1, l1, loc='upper left', framealpha=0.3, fontsize=9)
    ax.add_artist(leg1)
    
    ax.set_title('Market-Cycle Composite Indicator', fontsize=16)
    ax.set_ylabel('Composite Z-Score')
    ax.set_xlim(comp_sm.index[0], comp_sm.index[-1])
    
    ax.xaxis.set_major_locator(mdates.YearLocator(1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    
    plt.tight_layout()
    
    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plot_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    buf.close()
    
    return plot_base64

