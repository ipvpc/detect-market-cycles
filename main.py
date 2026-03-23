import pandas as pd
import numpy as np
from fredapi import Fred
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from datetime import datetime
import matplotlib.dates as mdates
import math
import os
import logging
import db_utils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

plt.style.use('dark_background')

# PARAMETERS
from datetime import timedelta
START = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
END = datetime.today().strftime('%Y-%m-%d')
FREQ          = 'ME'       # Pandas resample frequency for data (e.g. 'ME'=month‑end); controls aggregation period—higher freq ('D') adds noise, lower ('Q') smooths
SLOPE_WINDOW  = 3          # Look‑back periods for slope = comp.diff(SLOPE_WINDOW); larger values smooth and delay turn signals, smaller values speed detection but add volatility
SMOOTH_WINDOW = 2          # Window for composite moving average before plotting; larger windows yield a smoother but more lagged chart, smaller windows follow raw swings closely

# SERIES MAP
fred_map = {
    # growth / activity
    'LEI'               : 'USSLIND',           # Leading Index for US (Philly Fed state leading), proxy for overall LEI
    'Philly Manuf Diff' : 'GACDFSA066MSFRBPHI',# Philly Fed manufacturing diffusion index, proxy for ISM Mfg PMI (ISM is no longer supported at Fred)
    'Texas Serv Diff'   : 'TSSOSBACTUAMFRBDAL',# Dallas Fed services diffusion index, proxy for ISM Services PMI (ISM is no longer supported at Fred)
    'Capacity Util'     : 'CUMFNS',            # Industrial capacity utilization rate
    'BBK Leading'       : 'BBKMLEIX',          # Brave‑Butters‑Kelley leading index, leading growth component
    'CFNAI 3MMA'        : 'CFNAIMA3',          # Chicago Fed National Financial Activity Index 3‑mo avg

    # inflation sub‑block
    'Core CPI'          : 'CPILFESL',          # Core CPI ex‑food & energy, inflation proxy
    'Core PCE'          : 'PCEPILFE',          # Core PCE inflation proxy
    'Hourly Wage'       : 'CES0500000003',     # Avg hourly earnings YoY (BLS)
    'PPI'               : 'PPIACO',            # Producer Price Index commodities YoY
    'Commodities'       : 'PALLFNFINDEXM',     # BCOM commodity price index YoY

    # rates & credit
    '10Y'               : 'DGS10',             # 10‑year Treasury yield (Δ12m)
    'HY OAS'            : 'BAMLH0A0HYM2',      # High‑yield OAS (Δ12m, inverted)

    # stress proxy
    'StLouis FSI'       : 'STLFSI4',           # St. Louis Fed Financial Stress Index (inverted)
}

# Initialize FRED API client (key must be supplied via environment)
fred_api_key = os.getenv('FRED_API_KEY')
if not fred_api_key:
    raise SystemExit(
        'FRED_API_KEY is not set. Add it to your environment or .env file. '
        'See https://fred.stlouisfed.org/docs/api/api_key.html'
    )
fred = Fred(api_key=fred_api_key)

# Initialize database tables
try:
    db_utils.ensure_tables_exist()
    logger.info("Database tables initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize database tables: {e}. Continuing without database storage.")

# FETCH & RESAMPLE
raw = {}
for k, tkr in fred_map.items():
    try:
        data = fred.get_series(tkr, start=START, end=END)
        raw[k] = data
    except Exception as e:
        print(f"Warning: Could not fetch {k} ({tkr}): {e}")
        # Create empty series as fallback
        raw[k] = pd.Series(dtype=float)

df = pd.DataFrame(raw).resample(FREQ).last().ffill()

# Save raw data to database
try:
    db_utils.save_raw_data(df)
except Exception as e:
    logger.warning(f"Failed to save raw data to database: {e}")

# PLOT ALL SERIES

df_raw = df.copy()

# Determine grid size
n_series = len(df_raw.columns)
ncols    = 3
nrows    = math.ceil(n_series / ncols)

# sharex=False ⇒ each axis shows its own ticks
fig, axes = plt.subplots(
    nrows, ncols,
    figsize=(ncols*6, nrows*2.5),
    sharex=False
)

# Flatten axes for easy iteration
axes_flat = axes.flatten()

xmin, xmax = df_raw.index.min(), df_raw.index.max()

for ax, col in zip(axes_flat, df_raw.columns):
    ax.plot(df_raw.index, df_raw[col], lw=1, color='white')
    ax.set_title(col, fontsize=9)
    # enforce same x‐limits on each
    ax.set_xlim(xmin, xmax)
    # format each x‐axis independently
    ax.xaxis.set_major_locator(mdates.YearLocator(1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.tick_params(axis='y', labelsize=7)

# Turn off any unused subplots
for ax in axes_flat[n_series:]:
    ax.set_visible(False)

plt.tight_layout()
plt.show()

# TRANSFORMS
yoy     = lambda s: s.pct_change(12) * 100
delta12 = lambda s: s.diff(12)
invert  = lambda s: -s

df['LEI']           = yoy(df['LEI'])
df['Capacity Util'] = yoy(df['Capacity Util'])
df['BBK Leading']   = yoy(df['BBK Leading'])
for c in ['Core CPI','Core PCE','Hourly Wage','PPI','Commodities']:
    df[c] = yoy(df[c])
df['10Y']        = invert(delta12(df['10Y']))
df['HY OAS']     = invert(delta12(df['HY OAS']))
df['StLouis FSI']= invert(df['StLouis FSI'])

# INFLATION COMPOSITE
infl_cols = ['Core CPI','Core PCE','Hourly Wage','PPI','Commodities']
df['Inflation'] = df[infl_cols].mean(axis=1)

# Save transformed data to database
try:
    db_utils.save_transformed_data(df)
except Exception as e:
    logger.warning(f"Failed to save transformed data to database: {e}")

# FINAL INPUT LIST
inputs = [
    'LEI','Philly Manuf Diff','Texas Serv Diff',
    'Capacity Util','BBK Leading','CFNAI 3MMA',
    'Inflation','10Y','HY OAS','StLouis FSI'
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

comp    = z.mean(axis=1)
comp_sm = comp.rolling(SMOOTH_WINDOW, min_periods=1).mean()
slope   = comp.diff(SLOPE_WINDOW)

# PHASE CLASSIFICATION w/ DEAD‐ZONE
comp_thr, slope_thr = 0.15, 0.005
cond_early   = (comp < -comp_thr) & (slope >  slope_thr)
cond_midlate =  comp >  comp_thr
cond_decline = (comp < -comp_thr) & (slope < -slope_thr)
cond_unc     = comp.abs() <= comp_thr

# initial labels as a Series
phase = pd.Series('Mid-Late', index=comp.index)
phase[cond_early]   = 'Early'
phase[cond_decline] = 'Decline'
phase[cond_unc]     = 'Uncertain'

# map to integer codes
code_map = {'Early':0, 'Mid-Late':1, 'Decline':2, 'Uncertain':3}
inv_map  = {v:k for k,v in code_map.items()}
codes = phase.map(code_map)

# apply centered rolling‐mode
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
try:
    db_utils.save_composite_data(comp, comp_sm, slope, phase_series)
except Exception as e:
    logger.warning(f"Failed to save composite data to database: {e}")

phase_colors = {
    'Early'     : '#54d62c',
    'Mid-Late'  : '#3fa1ff',
    'Decline'   : '#ff4c4c',
    'Uncertain' : '#ffd400'
}

# S&P 500 YoY % via yfinance
data = yf.download('^GSPC',
                   start=START,
                   end=END,
                   auto_adjust=False,
                   progress=False)
# flatten multi-level columns
data.columns = data.columns.get_level_values(0)
spx = data['Adj Close'].resample(FREQ).last().ffill()
spx_yoy = spx.pct_change(12) * 100

# Save S&P 500 data to database
try:
    db_utils.save_sp500_data(spx_yoy)
except Exception as e:
    logger.warning(f"Failed to save S&P 500 data to database: {e}")

# PLOT
fig, ax = plt.subplots(figsize=(14,6))

mask = pd.Series(phase, index=comp.index)
grp  = (mask != mask.shift()).cumsum()
for ph, col in phase_colors.items():
    for _, span in mask[mask==ph].groupby(grp):
        ax.axvspan(span.index[0], span.index[-1],
                   color=col, alpha=0.20)

ax.plot(comp_sm.index, comp_sm,
        lw=2, color='white',
        label=f'Cycle Composite ({SMOOTH_WINDOW}-m MA)')
ax.axhline(0, color='#777', lw=1)

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
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1+h2, l1+l2,
          loc='upper left', framealpha=0.3,
          fontsize=9)
ax.add_artist(leg1)

ax.set_title('Market-Cycle Composite Indicator', fontsize=16)
ax.set_ylabel('Composite Z-Score')
ax.set_xlim(comp.index[0], comp.index[-1])


# major tick: every year
ax.xaxis.set_major_locator(mdates.YearLocator(1))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

plt.tight_layout()
plt.show()

# Dynamic Interpretation of Current Phase

# Use phase_series that was already created above
current_date    = phase_series.index[-1]
current_phase   = phase_series.iloc[-1]
current_comp    = comp_sm.loc[current_date]
current_slope   = slope.loc[current_date]
current_spx_yoy = spx_yoy.loc[current_date]

# Interpret by regime
if current_phase == 'Early':
    print(
        f"As of {current_date.date()}, the composite is {current_comp:.2f} "
        f"(+{current_slope:.3f} over {SLOPE_WINDOW}m) and S&P YoY is {current_spx_yoy:.1f}%. "
        "Early-phase conditions indicate nascent expansion. "
        "Leading activity indicators have bottomed and credit spreads are narrowing. "
        "Selective exposure to cyclical sectors may capture emerging growth while risks remain contained."
    )

elif current_phase == 'Mid-Late':
    print(
        f"As of {current_date.date()}, the composite stands at {current_comp:.2f} "
        f"(slope {current_slope:.3f}) with S&P YoY {current_spx_yoy:.1f}%. "
        "Mid-to-late cycle signals peak growth. "
        "Inflationary pressures and monetary tightening typically intensify in this phase. "
        "Shift allocation toward high-quality equities and defensive sectors to protect gains."
    )

elif current_phase == 'Decline':
    print(
        f"As of {current_date.date()}, the composite reads {current_comp:.2f} "
        f"(slope {current_slope:.3f}) and S&P YoY is {current_spx_yoy:.1f}%. "
        "Decline-phase patterns signal contraction. "
        "Risk sentiment deteriorates and liquidity tightens. "
        "Consider de-risking portfolios: increase fixed income, cash buffers, and low-volatility assets."
    )

elif current_phase == 'Uncertain':
    print(
        f"As of {current_date.date()}, the composite is neutral at {current_comp:.2f} "
        f"(slope {current_slope:.3f}) with S&P YoY {current_spx_yoy:.1f}%. "
        "Signals conflict and volatility often rises. "
        "Maintain balanced allocations, await clearer directional cues, and manage risk with disciplined stops."
    )

else:
    print("Phase classification unavailable.")


