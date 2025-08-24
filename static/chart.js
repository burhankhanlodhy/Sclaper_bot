class ChartAnalyzer {
    constructor() {
        this.chart = null;
        this.currentPair = window.CURRENT_PAIR;
        this.autoRefreshInterval = null;
    this.ws = null; // not used; rely on GlobalConnection
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadChartData();
    this.bindToGlobalConnection();
    }
    
    bindEvents() {
        // Timeframe selection
        document.querySelectorAll('input[name="timeframe"]').forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    this.loadChartData();
                }
            });
        });
        
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadChartData();
        });
        
        // Auto refresh toggle
        document.getElementById('autoRefresh').addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });
        
        // Start auto refresh by default
        this.startAutoRefresh();
    }
    
    bindToGlobalConnection() {
        window.addEventListener('ws:update', (e) => {
            const data = e.detail;
            if (data.type === 'update') {
                this.handleRealtimeUpdate(data);
            }
        });
        if (window.GlobalConnection) {
            setTimeout(() => window.GlobalConnection.updateStatusBadge(), 0);
        }
    }
    
    handleRealtimeUpdate(data) {
        // Update current price display
        document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
    }
    
    startAutoRefresh() {
        this.stopAutoRefresh(); // Clear any existing interval
        this.autoRefreshInterval = setInterval(() => {
            this.loadChartData();
        }, 30000); // Refresh every 30 seconds
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
    
    async loadChartData() {
        try {
            const timeframe = document.querySelector('input[name="timeframe"]:checked').value;
            const limit = this.getTimeframeLimits(timeframe);
            
            const response = await fetch(`/api/chart/${this.currentPair}?timeframe=${timeframe}&limit=${limit}`);
            const result = await response.json();
            
            if (result.success) {
                this.renderChart(result.data);
                this.updateTechnicalIndicators(result.data.technical);
                this.updatePriceTable(result.data.prices, result.data.technical);
            } else {
                this.showError('Failed to load chart data: ' + result.error);
            }
        } catch (error) {
            console.error('Error loading chart data:', error);
            this.showError('Network error loading chart data');
        }
    }
    
    getTimeframeLimits(timeframe) {
        const limits = {
            '1h': 100,
            '4h': 200,
            '1d': 365
        };
        return limits[timeframe] || 100;
    }
    
    renderChart(data) {
        const ctx = document.getElementById('priceChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.chart) {
            this.chart.destroy();
        }
        
        const labels = data.prices.map(p => {
            const date = new Date(p.timestamp);
            return date.toLocaleString();
        });
        
        const prices = data.prices.map(p => parseFloat(p.price));
        const sma5 = data.technical.sma_5 || [];
        const sma20 = data.technical.sma_20 || [];
        const bollingerUpper = data.technical.bollinger_upper || [];
        const bollingerLower = data.technical.bollinger_lower || [];
        const bollingerMiddle = data.technical.bollinger_middle || [];
        
        // Update current price and change
        if (prices.length > 1) {
            const currentPrice = prices[prices.length - 1];
            const previousPrice = prices[prices.length - 2];
            const change = ((currentPrice - previousPrice) / previousPrice) * 100;
            
            document.getElementById('currentPrice').textContent = `$${currentPrice.toFixed(4)}`;
            
            const changeElement = document.getElementById('priceChange');
            changeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
            changeElement.className = `badge ${change >= 0 ? 'bg-success' : 'bg-danger'}`;
        }
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Price',
                        data: prices,
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        order: 1
                    },
                    {
                        label: 'SMA 5',
                        data: sma5,
                        borderColor: '#28a745',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        fill: false,
                        pointRadius: 0,
                        order: 2
                    },
                    {
                        label: 'SMA 20',
                        data: sma20,
                        borderColor: '#17a2b8',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        fill: false,
                        pointRadius: 0,
                        order: 3
                    },
                    {
                        label: 'Bollinger Upper',
                        data: bollingerUpper,
                        borderColor: '#ffc107',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        fill: false,
                        pointRadius: 0,
                        borderDash: [5, 5],
                        order: 4
                    },
                    {
                        label: 'Bollinger Lower',
                        data: bollingerLower,
                        borderColor: '#ffc107',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        fill: false,
                        pointRadius: 0,
                        borderDash: [5, 5],
                        order: 5
                    },
                    {
                        label: 'Bollinger Middle',
                        data: bollingerMiddle,
                        borderColor: '#fd7e14',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        fill: false,
                        pointRadius: 0,
                        borderDash: [2, 2],
                        order: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += '$' + context.parsed.y.toFixed(4);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        },
                        ticks: {
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Price (USD)'
                        },
                        position: 'left'
                    }
                }
            }
        });
        
        // Update data points count
        document.getElementById('dataPoints').textContent = prices.length;
    }
    
    updateTechnicalIndicators(technical) {
        if (!technical || Object.keys(technical).length === 0) {
            return;
        }
        
        const sma5 = technical.sma_5;
        const sma20 = technical.sma_20;
        const bollingerUpper = technical.bollinger_upper;
        const bollingerLower = technical.bollinger_lower;
        const bollingerMiddle = technical.bollinger_middle;
        
        // Update SMA values
        if (sma5 && sma5.length > 0) {
            const lastSMA5 = sma5[sma5.length - 1];
            document.getElementById('sma5Value').textContent = lastSMA5 ? `$${lastSMA5.toFixed(4)}` : 'N/A';
        }
        
        if (sma20 && sma20.length > 0) {
            const lastSMA20 = sma20[sma20.length - 1];
            document.getElementById('sma20Value').textContent = lastSMA20 ? `$${lastSMA20.toFixed(4)}` : 'N/A';
        }
        
        // Update Bollinger Bands
        if (bollingerUpper && bollingerUpper.length > 0) {
            const lastUpper = bollingerUpper[bollingerUpper.length - 1];
            const lastLower = bollingerLower[bollingerLower.length - 1];
            const lastMiddle = bollingerMiddle[bollingerMiddle.length - 1];
            
            document.getElementById('bollingerUpper').textContent = lastUpper ? `$${lastUpper.toFixed(4)}` : 'N/A';
            document.getElementById('bollingerLower').textContent = lastLower ? `$${lastLower.toFixed(4)}` : 'N/A';
            document.getElementById('bollingerMiddle').textContent = lastMiddle ? `$${lastMiddle.toFixed(4)}` : 'N/A';
        }
        
        // Generate signals
        this.generateSignals(sma5, sma20, bollingerUpper, bollingerLower);
    }
    
    generateSignals(sma5, sma20, bollingerUpper, bollingerLower) {
        const maSignalElement = document.getElementById('maSignal');
        const bbSignalElement = document.getElementById('bbSignal');
        
        // Moving Average Signal
        if (sma5 && sma20 && sma5.length > 1 && sma20.length > 1) {
            const currentSMA5 = sma5[sma5.length - 1];
            const currentSMA20 = sma20[sma20.length - 1];
            
            if (currentSMA5 && currentSMA20) {
                if (currentSMA5 > currentSMA20) {
                    maSignalElement.textContent = 'Bullish';
                    maSignalElement.className = 'badge bg-success';
                } else {
                    maSignalElement.textContent = 'Bearish';
                    maSignalElement.className = 'badge bg-danger';
                }
            }
        }
        
        // Bollinger Bands Signal
        if (bollingerUpper && bollingerLower && bollingerUpper.length > 0) {
            const currentPrice = parseFloat(document.getElementById('currentPrice').textContent.replace('$', ''));
            const currentUpper = bollingerUpper[bollingerUpper.length - 1];
            const currentLower = bollingerLower[bollingerLower.length - 1];
            
            if (currentPrice && currentUpper && currentLower) {
                if (currentPrice >= currentUpper) {
                    bbSignalElement.textContent = 'Overbought';
                    bbSignalElement.className = 'badge bg-danger';
                } else if (currentPrice <= currentLower) {
                    bbSignalElement.textContent = 'Oversold';
                    bbSignalElement.className = 'badge bg-success';
                } else {
                    bbSignalElement.textContent = 'Neutral';
                    bbSignalElement.className = 'badge bg-secondary';
                }
            }
        }
    }
    
    updatePriceTable(prices, technical) {
        const tbody = document.getElementById('priceDataTable');
        
        if (!prices || prices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No price data available</td></tr>';
            return;
        }
        
        // Show last 10 entries
        const recentPrices = prices.slice(-10).reverse();
        const sma5 = technical.sma_5 || [];
        const sma20 = technical.sma_20 || [];
        
        tbody.innerHTML = recentPrices.map((price, index) => {
            const originalIndex = prices.length - 1 - index;
            const sma5Value = sma5[originalIndex];
            const sma20Value = sma20[originalIndex];
            
            return `
                <tr>
                    <td>${new Date(price.timestamp).toLocaleTimeString()}</td>
                    <td><strong>$${parseFloat(price.price).toFixed(4)}</strong></td>
                    <td>${price.bid ? '$' + parseFloat(price.bid).toFixed(4) : 'N/A'}</td>
                    <td>${price.ask ? '$' + parseFloat(price.ask).toFixed(4) : 'N/A'}</td>
                    <td>${price.volume ? parseFloat(price.volume).toFixed(2) : 'N/A'}</td>
                    <td class="text-success">${sma5Value ? '$' + sma5Value.toFixed(4) : 'N/A'}</td>
                    <td class="text-info">${sma20Value ? '$' + sma20Value.toFixed(4) : 'N/A'}</td>
                </tr>
            `;
        }).join('');
    }
    
    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alert.style.top = '20px';
        alert.style.right = '20px';
        alert.style.zIndex = '9999';
        alert.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alert);
        
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }
    
    destroy() {
        this.stopAutoRefresh();
    // No explicit WS to close; GlobalConnection persists across pages
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

// Initialize chart analyzer when page loads
let chartAnalyzer;
document.addEventListener('DOMContentLoaded', () => {
    chartAnalyzer = new ChartAnalyzer();
});

// Clean up when page unloads
window.addEventListener('beforeunload', () => {
    if (chartAnalyzer) {
        chartAnalyzer.destroy();
    }
});
