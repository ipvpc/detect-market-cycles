/**
 * Alpha5 Market Cycle Intelligence - Main Application
 * Handles API integration, chart rendering, and UI updates
 */

class MarketCycleApp {
    constructor() {
        this.apiBase = '';
        this.chart = null;
        this.currentData = null;
        this.autoRefreshInterval = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDateInputs();
        this.loadInitialData();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadInitialData();
        });

        // Analyze button
        document.getElementById('analyze-btn').addEventListener('click', () => {
            this.runAnalysis();
        });

        // Chart view controls
        document.querySelectorAll('.control-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.control-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                const view = e.target.dataset.view;
                this.updateChartView(view);
            });
        });

        // Indicator filters
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                const filter = e.target.dataset.filter;
                this.filterIndicators(filter);
            });
        });
    }

    setupDateInputs() {
        const today = new Date();
        const oneYearAgo = new Date(today);
        oneYearAgo.setFullYear(today.getFullYear() - 1);

        document.getElementById('end-date').value = today.toISOString().split('T')[0];
        document.getElementById('start-date').value = oneYearAgo.toISOString().split('T')[0];
    }

    async loadInitialData() {
        this.showLoading();
        try {
            const response = await fetch(`${this.apiBase}/analyze?generate_plot=false`);
            if (!response.ok) throw new Error('Failed to fetch data');
            
            const data = await response.json();
            this.currentData = data;
            this.updateUI(data);
            this.updateChart(data);
            this.updateIndicators(data);
            this.updateLastUpdate();
            this.showToast('Data loaded successfully', 'success');
        } catch (error) {
            console.error('Error loading data:', error);
            this.showToast('Failed to load data: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async runAnalysis() {
        this.showLoading();
        try {
            const params = this.getAnalysisParameters();
            const queryString = new URLSearchParams(params).toString();
            
            const response = await fetch(`${this.apiBase}/analyze?${queryString}&generate_plot=false`);
            if (!response.ok) throw new Error('Analysis failed');
            
            const data = await response.json();
            this.currentData = data;
            this.updateUI(data);
            this.updateChart(data);
            this.updateIndicators(data);
            this.updateLastUpdate();
            this.showToast('Analysis completed successfully', 'success');
        } catch (error) {
            console.error('Error running analysis:', error);
            this.showToast('Analysis failed: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }

    getAnalysisParameters() {
        return {
            start_date: document.getElementById('start-date').value || null,
            end_date: document.getElementById('end-date').value || null,
            freq: document.getElementById('freq-select').value,
            slope_window: parseInt(document.getElementById('slope-window').value),
            smooth_window: parseInt(document.getElementById('smooth-window').value),
            save_to_db: 'true',
            generate_plot: 'false'
        };
    }

    updateUI(data) {
        // Update phase indicator
        const phase = data.current_phase || 'Uncertain';
        const phaseElement = document.getElementById('phase-indicator');
        const phaseLabel = document.getElementById('phase-label');
        
        phaseElement.textContent = phase.charAt(0);
        phaseElement.className = 'phase-indicator ' + phase.toLowerCase().replace('-', '');
        phaseLabel.textContent = phase;

        // Update metrics
        document.getElementById('composite-score').textContent = 
            data.current_composite !== null ? data.current_composite.toFixed(3) : '--';
        document.getElementById('slope-value').textContent = 
            data.current_slope !== null ? data.current_slope.toFixed(4) : '--';
        document.getElementById('sp500-yoy').textContent = 
            data.current_sp500_yoy !== null ? data.current_sp500_yoy.toFixed(2) + '%' : '--';

        // Update interpretation
        document.getElementById('phase-interpretation').textContent = 
            data.interpretation || 'No interpretation available.';
    }

    updateChart(data) {
        const ctx = document.getElementById('main-chart').getContext('2d');
        
        if (this.chart) {
            this.chart.destroy();
        }

        const compositeData = data.data.composite_scores;
        const sp500Data = data.data.sp500_yoy;
        
        if (!compositeData || !compositeData.dates || compositeData.dates.length === 0) {
            console.error('No chart data available');
            return;
        }
        
        const dates = compositeData.dates.map(d => new Date(d));
        const composite = compositeData.composite_smoothed || [];
        const phases = compositeData.phases || [];
        const sp500Values = sp500Data && sp500Data.values ? sp500Data.values : [];

        // Phase colors
        const phaseColors = {
            'Early': 'rgba(16, 185, 129, 0.3)',
            'Mid-Late': 'rgba(59, 130, 246, 0.3)',
            'Decline': 'rgba(239, 68, 68, 0.3)',
            'Uncertain': 'rgba(245, 158, 11, 0.3)'
        };

        // Create phase background datasets using area charts
        const phaseDatasets = [];
        if (phases.length > 0) {
            let currentPhase = phases[0];
            let phaseStart = 0;

            for (let i = 1; i < phases.length; i++) {
                if (phases[i] !== currentPhase) {
                    const phaseDates = dates.slice(phaseStart, i);
                    const phaseValues = composite.slice(phaseStart, i);
                    // Create area chart data points
                    const phaseData = phaseDates.map((date, idx) => ({
                        x: date,
                        y: phaseValues[idx] || 0
                    }));
                    
                    phaseDatasets.push({
                        label: currentPhase,
                        data: phaseData,
                        type: 'line',
                        backgroundColor: phaseColors[currentPhase] || 'rgba(128, 128, 128, 0.1)',
                        borderColor: 'transparent',
                        borderWidth: 0,
                        pointRadius: 0,
                        fill: 'origin',
                        order: 0,
                        tension: 0.4
                    });
                    phaseStart = i;
                    currentPhase = phases[i];
                }
            }
            // Add last phase
            const phaseDates = dates.slice(phaseStart);
            const phaseValues = composite.slice(phaseStart);
            const phaseData = phaseDates.map((date, idx) => ({
                x: date,
                y: phaseValues[idx] || 0
            }));
            
            phaseDatasets.push({
                label: currentPhase,
                data: phaseData,
                type: 'line',
                backgroundColor: phaseColors[currentPhase] || 'rgba(128, 128, 128, 0.1)',
                borderColor: 'transparent',
                borderWidth: 0,
                pointRadius: 0,
                fill: 'origin',
                order: 0,
                tension: 0.4
            });
        }

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    ...phaseDatasets,
                    {
                        label: 'Composite Score',
                        data: dates.map((date, idx) => ({ x: date, y: composite[idx] || 0 })),
                        borderColor: '#00d4ff',
                        backgroundColor: 'rgba(0, 212, 255, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0,
                        order: 2
                    },
                    {
                        label: 'S&P 500 YoY %',
                        data: dates.map((date, idx) => ({ x: date, y: sp500Values[idx] || null })),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0,
                        yAxisID: 'y1',
                        order: 1,
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#a0a0b0',
                            font: {
                                family: 'Inter',
                                size: 12
                            },
                            filter: (item) => {
                                // Only show main datasets in legend
                                return item.datasetIndex >= phaseDatasets.length;
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(20, 20, 32, 0.95)',
                        titleColor: '#ffffff',
                        bodyColor: '#a0a0b0',
                        borderColor: '#00d4ff',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        callbacks: {
                            title: (items) => {
                                return new Date(items[0].label).toLocaleDateString();
                            },
                            label: (context) => {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y.toFixed(3);
                                    if (context.dataset.label === 'S&P 500 YoY %') {
                                        label += '%';
                                    }
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month',
                            displayFormats: {
                                month: 'MMM yyyy'
                            }
                        },
                        grid: {
                            color: 'rgba(37, 37, 53, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#6b6b7a',
                            font: {
                                family: 'JetBrains Mono',
                                size: 11
                            }
                        }
                    },
                    y: {
                        position: 'left',
                        grid: {
                            color: 'rgba(37, 37, 53, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#6b6b7a',
                            font: {
                                family: 'JetBrains Mono',
                                size: 11
                            }
                        },
                        title: {
                            display: true,
                            text: 'Composite Z-Score',
                            color: '#00d4ff',
                            font: {
                                family: 'Inter',
                                size: 12,
                                weight: '600'
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: '#10b981',
                            font: {
                                family: 'JetBrains Mono',
                                size: 11
                            }
                        },
                        title: {
                            display: true,
                            text: 'S&P 500 YoY %',
                            color: '#10b981',
                            font: {
                                family: 'Inter',
                                size: 12,
                                weight: '600'
                            }
                        }
                    }
                }
            }
        });

        // Set initial view
        this.updateChartView('both');
    }

    updateChartView(view) {
        if (!this.chart) return;

        const compositeDataset = this.chart.data.datasets.find(d => d.label === 'Composite Score');
        const sp500Dataset = this.chart.data.datasets.find(d => d.label === 'S&P 500 YoY %');

        if (view === 'composite') {
            if (compositeDataset) compositeDataset.hidden = false;
            if (sp500Dataset) sp500Dataset.hidden = true;
        } else if (view === 'sp500') {
            if (compositeDataset) compositeDataset.hidden = true;
            if (sp500Dataset) sp500Dataset.hidden = false;
        } else { // both
            if (compositeDataset) compositeDataset.hidden = false;
            if (sp500Dataset) sp500Dataset.hidden = false;
        }

        this.chart.update();
    }

    updateIndicators(data) {
        const grid = document.getElementById('indicators-grid');
        grid.innerHTML = '';

        const transformedSeries = data.data.transformed_series;
        const series = transformedSeries.series;
        const dates = transformedSeries.dates;
        const lastIndex = dates.length - 1;

        // Indicator categories
        const categories = {
            growth: ['LEI', 'Philly Manuf Diff', 'Texas Serv Diff', 'Capacity Util', 'BBK Leading', 'CFNAI 3MMA'],
            inflation: ['Core CPI', 'Core PCE', 'Hourly Wage', 'PPI', 'Commodities', 'Inflation'],
            rates: ['10Y', 'HY OAS', 'StLouis FSI']
        };

        // Create indicator items
        Object.keys(series).forEach(key => {
            const values = series[key];
            const currentValue = values[lastIndex];
            const previousValue = values[lastIndex - 1] || currentValue;
            const trend = currentValue > previousValue ? 'up' : 'down';

            // Determine category
            let category = 'all';
            if (categories.growth.includes(key)) category = 'growth';
            else if (categories.inflation.includes(key)) category = 'inflation';
            else if (categories.rates.includes(key)) category = 'rates';

            const item = document.createElement('div');
            item.className = `indicator-item ${category}`;
            item.dataset.category = category;
            item.innerHTML = `
                <div class="indicator-name">${key}</div>
                <div class="indicator-value">${currentValue.toFixed(2)}</div>
                <div class="indicator-trend ${trend}">
                    ${trend === 'up' ? '↑' : '↓'} ${Math.abs(currentValue - previousValue).toFixed(2)}
                </div>
            `;
            grid.appendChild(item);
        });
    }

    filterIndicators(filter) {
        const items = document.querySelectorAll('.indicator-item');
        items.forEach(item => {
            if (filter === 'all' || item.dataset.category === filter) {
                item.classList.remove('hidden');
            } else {
                item.classList.add('hidden');
            }
        });
    }

    updateLastUpdate() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { 
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        document.getElementById('last-update').textContent = timeString;
    }

    showLoading() {
        document.getElementById('loading-overlay').classList.add('active');
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.remove('active');
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        
        toastMessage.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    startAutoRefresh() {
        // Auto-refresh every 5 minutes
        this.autoRefreshInterval = setInterval(() => {
            this.loadInitialData();
        }, 5 * 60 * 1000);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MarketCycleApp();
});

// Handle page visibility for auto-refresh
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        window.app?.stopAutoRefresh();
    } else {
        window.app?.startAutoRefresh();
    }
});

