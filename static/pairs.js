class PairsManager {
    constructor() {
        this.currentModal = null;
        this.quickChart = null;
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadTopPairs();
        this.bindToGlobalConnection();
    }
    
    bindToGlobalConnection() {
        // Ensure the shared status badge is updated
        if (window.GlobalConnection) {
            setTimeout(() => window.GlobalConnection.updateStatusBadge(), 0);
        }
        // We currently don't need WS updates here, but keep the hook
        window.addEventListener('ws:update', (e) => {
            // Future: react to updates if needed
        });
    }
    
    bindEvents() {
        // Search functionality
        document.getElementById('searchBtn').addEventListener('click', () => {
            this.searchPairs();
        });
        
        document.getElementById('clearBtn').addEventListener('click', () => {
            this.clearSearch();
        });
        
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchPairs();
            }
        });
        
        // Load all pairs button
        document.getElementById('loadAllPairsBtn').addEventListener('click', () => {
            this.toggleAllPairs();
        });
    }
    
    async loadTopPairs() {
        try {
            const response = await fetch('/api/pairs/top10');
            const result = await response.json();
            
            if (result.success) {
                this.displayTopPairs(result.data);
            } else {
                this.showError('Failed to load top pairs: ' + result.error);
            }
        } catch (error) {
            console.error('Error loading top pairs:', error);
            this.showError('Network error loading top pairs');
        }
    }
    
    displayTopPairs(pairs) {
        const tbody = document.getElementById('topPairsTable');
        
        if (pairs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No top pairs data available</td></tr>';
            return;
        }
        
        tbody.innerHTML = pairs.map((pair, index) => `
            <tr>
                <td><span class="badge bg-warning">#${index + 1}</span></td>
                <td>
                    <strong>${pair.symbol}</strong>
                    <small class="text-muted d-block">${pair.altname || ''}</small>
                </td>
                <td>
                    <span class="badge bg-info">${pair.base_currency}</span>
                </td>
                <td>
                    ${pair.latest_price ? '$' + parseFloat(pair.latest_price).toFixed(4) : 'N/A'}
                </td>
                <td>
                    ${pair.volume ? this.formatVolume(pair.volume) : 'N/A'}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="pairsManager.showQuickChart('${pair.symbol}')">
                            <i class="fas fa-chart-line"></i> Quick Chart
                        </button>
                        <button class="btn btn-outline-success" onclick="pairsManager.openFullChart('${pair.symbol}')">
                            <i class="fas fa-external-link-alt"></i> Full Chart
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }
    
    async searchPairs() {
        const query = document.getElementById('searchInput').value.trim();
        
        try {
            const response = await fetch(`/api/pairs/search?query=${encodeURIComponent(query)}`);
            const result = await response.json();
            
            if (result.success) {
                this.displaySearchResults(result.data, query);
            } else {
                this.showError('Search failed: ' + result.error);
            }
        } catch (error) {
            console.error('Error searching pairs:', error);
            this.showError('Network error during search');
        }
    }
    
    displaySearchResults(pairs, query) {
        const section = document.getElementById('searchResultsSection');
        const tbody = document.getElementById('searchResultsTable');
        
        section.style.display = 'block';
        
        if (pairs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No pairs found for "${query}"</td></tr>`;
            return;
        }
        
        tbody.innerHTML = pairs.map(pair => `
            <tr>
                <td>
                    <strong>${pair.symbol}</strong>
                    <small class="text-muted d-block">${pair.altname || ''}</small>
                </td>
                <td>
                    <span class="badge bg-info">${pair.base_currency}</span>
                </td>
                <td>
                    ${pair.latest_price ? '$' + parseFloat(pair.latest_price).toFixed(4) : 'N/A'}
                </td>
                <td>
                    <span class="badge ${pair.status === 'online' ? 'bg-success' : 'bg-warning'}">
                        ${pair.status || 'Unknown'}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="pairsManager.showQuickChart('${pair.symbol}')">
                            <i class="fas fa-chart-line"></i>
                        </button>
                        <button class="btn btn-outline-success" onclick="pairsManager.openFullChart('${pair.symbol}')">
                            <i class="fas fa-external-link-alt"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }
    
    clearSearch() {
        document.getElementById('searchInput').value = '';
        document.getElementById('searchResultsSection').style.display = 'none';
    }
    
    async toggleAllPairs() {
        const button = document.getElementById('loadAllPairsBtn');
        const body = document.getElementById('allPairsBody');
        
        if (body.style.display === 'none') {
            button.innerHTML = '<div class="spinner-border spinner-border-sm me-2"></div>Loading...';
            await this.loadAllPairs();
            body.style.display = 'block';
            // Button text is updated in loadAllPairs() to show count
        } else {
            body.style.display = 'none';
            button.innerHTML = '<i class="fas fa-eye me-2"></i>Show All Pairs';
        }
    }
    
    async loadAllPairs() {
        try {
            const response = await fetch('/api/pairs/all');
            const result = await response.json();
            
            if (result.success) {
                this.displayAllPairs(result.data);
                // Update button to show count
                const button = document.getElementById('loadAllPairsBtn');
                const countText = result.total ? ` (${result.total} pairs)` : '';
                button.innerHTML = `<i class="fas fa-eye-slash me-2"></i>Hide All Pairs${countText}`;
            } else {
                this.showError('Failed to load all pairs: ' + result.error);
            }
        } catch (error) {
            console.error('Error loading all pairs:', error);
            this.showError('Network error loading all pairs');
        }
    }
    
    displayAllPairs(pairs) {
        const tbody = document.getElementById('allPairsTable');
        
        // Add a header with count
        const cardBody = document.getElementById('allPairsBody');
        let existingInfo = cardBody.querySelector('.pairs-info');
        if (existingInfo) {
            existingInfo.remove();
        }
        
        const infoDiv = document.createElement('div');
        infoDiv.className = 'pairs-info alert alert-info mb-3';
        infoDiv.innerHTML = `
            <i class="fas fa-info-circle me-2"></i>
            Showing <strong>${pairs.length}</strong> USD trading pairs. 
            You can search for specific pairs using the search box above.
        `;
        cardBody.insertBefore(infoDiv, cardBody.firstChild);
        
        tbody.innerHTML = pairs.map(pair => `
            <tr>
                <td>
                    <strong>${pair.symbol}</strong>
                    <small class="text-muted d-block">${pair.base_currency}/USD</small>
                </td>
                <td><span class="badge bg-info">${pair.base_currency}</span></td>
                <td>
                    ${pair.latest_price ? '$' + parseFloat(pair.latest_price).toFixed(6) : '<span class="text-muted">No data</span>'}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary btn-sm" onclick="pairsManager.showQuickChart('${pair.symbol}')" title="Quick Chart">
                            <i class="fas fa-chart-line"></i>
                        </button>
                        <button class="btn btn-outline-success btn-sm" onclick="pairsManager.openFullChart('${pair.symbol}')" title="Full Chart">
                            <i class="fas fa-external-link-alt"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }
    
    async showQuickChart(pair) {
        const modal = new bootstrap.Modal(document.getElementById('quickChartModal'));
        document.getElementById('modalPairTitle').innerHTML = `<i class="fas fa-chart-area me-2"></i>${pair} Quick Chart`;
        
        // Show loading state
        document.getElementById('quickChartContainer').innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading chart...</span>
                </div>
                <p class="mt-2">Loading chart data for ${pair}...</p>
            </div>
        `;
        
        modal.show();
        this.currentModal = pair;
        
        try {
            const response = await fetch(`/api/chart/${pair}?limit=50`);
            const result = await response.json();
            
            if (result.success) {
                this.renderQuickChart(result.data);
            } else {
                this.showChartError('Failed to load chart data: ' + result.error);
            }
        } catch (error) {
            console.error('Error loading chart data:', error);
            this.showChartError('Network error loading chart data');
        }
        
        // Set up full chart button
        document.getElementById('openFullChartBtn').onclick = () => {
            this.openFullChart(pair);
        };
    }
    
    renderQuickChart(data) {
        const container = document.getElementById('quickChartContainer');
        container.innerHTML = '<canvas id="quickChart"></canvas>';
        
        const ctx = document.getElementById('quickChart').getContext('2d');
        
        const labels = data.prices.map(p => new Date(p.timestamp).toLocaleTimeString());
        const prices = data.prices.map(p => parseFloat(p.price));
        
        this.quickChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Price',
                    data: prices,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Price (USD)'
                        }
                    }
                }
            }
        });
    }
    
    showChartError(message) {
        document.getElementById('quickChartContainer').innerHTML = `
            <div class="alert alert-danger text-center">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    }
    
    openFullChart(pair) {
        window.open(`/chart/${pair}`, '_blank');
    }
    
    formatVolume(volume) {
        if (volume >= 1000000) {
            return (volume / 1000000).toFixed(2) + 'M';
        } else if (volume >= 1000) {
            return (volume / 1000).toFixed(2) + 'K';
        } else {
            return volume.toFixed(2);
        }
    }
    
    showError(message) {
        // Create a temporary alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alert.style.top = '20px';
        alert.style.right = '20px';
        alert.style.zIndex = '9999';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }
}

// Initialize pairs manager when page loads
let pairsManager;
document.addEventListener('DOMContentLoaded', () => {
    pairsManager = new PairsManager();
});
