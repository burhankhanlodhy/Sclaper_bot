class PriceDataManager {
    constructor() {
        this.currentData = [];
        this.allSymbols = [];
        this.currentPage = 1;
        this.itemsPerPage = 50;
        this.autoRefreshInterval = null;
    this.websocket = null; // replaced by GlobalConnection events
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
    this.bindToGlobalConnection();
        this.loadSymbols();
        this.loadPriceData();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Filter controls
        document.getElementById('symbolFilter').addEventListener('change', () => {
            this.loadPriceData();
        });
        
        document.getElementById('limitFilter').addEventListener('change', () => {
            this.loadPriceData();
        });
        
        // Buttons
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadPriceData();
        });
        
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportToCSV();
        });
        
        // Auto refresh toggle
        document.getElementById('autoRefresh').addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });
    }
    
    bindToGlobalConnection() {
        window.addEventListener('ws:update', (e) => {
            const data = e.detail;
            this.handleWebSocketMessage(data);
        });
        if (window.GlobalConnection) {
            setTimeout(() => window.GlobalConnection.updateStatusBadge(), 0);
        }
    }
    
    handleWebSocketMessage(data) {
        if (data.type === 'price_update') {
            // Update real-time data
            this.updateLastUpdateTime();
        }
    }
    
    // Connection status is managed globally by connection.js
    
    updateLastUpdateTime() {
        const now = new Date();
    const el = document.getElementById('latestUpdate') || document.getElementById('lastUpdate');
    if (el) el.textContent = now.toLocaleTimeString();
    }
    
    async loadSymbols() {
        try {
            const response = await fetch('/api/price-data/symbols');
            const result = await response.json();
            
            if (result.success) {
                this.allSymbols = result.data;
                this.populateSymbolFilter();
            }
        } catch (error) {
            console.error('Error loading symbols:', error);
        }
    }
    
    populateSymbolFilter() {
        const symbolFilter = document.getElementById('symbolFilter');
        
        // Clear existing options except the first one
        symbolFilter.innerHTML = '<option value="">All Symbols</option>';
        
        // Add symbol options
        this.allSymbols.forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol;
            symbolFilter.appendChild(option);
        });
    }
    
    async loadPriceData() {
        this.showLoading(true);
        
        try {
            const symbol = document.getElementById('symbolFilter').value;
            const limit = document.getElementById('limitFilter').value;
            
            let url = `/api/price-data?limit=${limit}`;
            if (symbol) {
                url += `&symbol=${encodeURIComponent(symbol)}`;
            }
            
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success) {
                this.currentData = result.data;
                this.renderPriceData();
                this.updateSummaryCards();
            } else {
                this.showError('Failed to load price data: ' + result.error);
            }
        } catch (error) {
            console.error('Error loading price data:', error);
            this.showError('Network error while loading price data');
        } finally {
            this.showLoading(false);
        }
    }
    
    renderPriceData() {
        const tbody = document.getElementById('priceDataTable');
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const pageData = this.currentData.slice(startIndex, endIndex);
        
        if (pageData.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center py-4 text-muted">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        No price data found with current filters
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = pageData.map(record => {
            const spread = record.ask && record.bid ? (record.ask - record.bid).toFixed(6) : '-';
            const spreadPercent = record.ask && record.bid && record.price ? 
                (((record.ask - record.bid) / record.price) * 100).toFixed(4) : '';
            
            return `
                <tr>
                    <td><span class="badge bg-secondary">${record.id}</span></td>
                    <td>
                        <strong>${record.symbol}</strong>
                        <a href="/chart/${record.symbol}" class="ms-2 text-decoration-none" title="View Chart">
                            <i class="fas fa-chart-line"></i>
                        </a>
                    </td>
                    <td><strong>$${this.formatNumber(record.price)}</strong></td>
                    <td class="text-success">$${this.formatNumber(record.bid)}</td>
                    <td class="text-danger">$${this.formatNumber(record.ask)}</td>
                    <td>
                        ${spread !== '-' ? `$${spread}` : '-'}
                        ${spreadPercent ? `<br><small class="text-muted">(${spreadPercent}%)</small>` : ''}
                    </td>
                    <td>${this.formatVolume(record.volume)}</td>
                    <td>
                        <span title="${record.timestamp}">
                            ${this.formatTimestamp(record.timestamp)}
                        </span>
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary btn-sm" 
                                    onclick="priceDataManager.viewChart('${record.symbol}')" 
                                    title="View Chart">
                                <i class="fas fa-chart-line"></i>
                            </button>
                            <button class="btn btn-outline-info btn-sm" 
                                    onclick="priceDataManager.copyPrice('${record.price}')" 
                                    title="Copy Price">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
        this.updateRecordsCount();
        this.renderPagination();
    }
    
    formatNumber(value) {
        if (!value) return '0.00';
        return parseFloat(value).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 8
        });
    }
    
    formatVolume(value) {
        if (!value) return '-';
        const num = parseFloat(value);
        if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
        return num.toFixed(2);
    }
    
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    
    updateSummaryCards() {
        document.getElementById('totalRecords').textContent = this.currentData.length.toLocaleString();
        
        const uniqueSymbols = new Set(this.currentData.map(d => d.symbol));
        document.getElementById('totalSymbols').textContent = uniqueSymbols.size.toLocaleString();
        
        if (this.currentData.length > 0) {
            const latestRecord = this.currentData[0];
            document.getElementById('latestUpdate').textContent = this.formatTimestamp(latestRecord.timestamp);
            
            // Calculate average update frequency (seconds between updates)
            if (this.currentData.length > 1) {
                const times = this.currentData.slice(0, 10).map(d => new Date(d.timestamp).getTime());
                const intervals = [];
                for (let i = 0; i < times.length - 1; i++) {
                    intervals.push((times[i] - times[i + 1]) / 1000);
                }
                const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
                document.getElementById('dataFrequency').textContent = `${avgInterval.toFixed(1)}s`;
            }
        }
    }
    
    updateRecordsCount() {
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = Math.min(startIndex + this.itemsPerPage, this.currentData.length);
        document.getElementById('recordsShown').textContent = 
            `${startIndex + 1}-${endIndex} of ${this.currentData.length} records`;
    }
    
    renderPagination() {
        const totalPages = Math.ceil(this.currentData.length / this.itemsPerPage);
        const pagination = document.getElementById('pagination');
        
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }
        
        let paginationHtml = '';
        
        // Previous button
        paginationHtml += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="priceDataManager.goToPage(${this.currentPage - 1})">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
        
        // Page numbers
        const startPage = Math.max(1, this.currentPage - 2);
        const endPage = Math.min(totalPages, this.currentPage + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="priceDataManager.goToPage(${i})">${i}</a>
                </li>
            `;
        }
        
        // Next button
        paginationHtml += `
            <li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="priceDataManager.goToPage(${this.currentPage + 1})">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
        
        pagination.innerHTML = paginationHtml;
    }
    
    goToPage(page) {
        const totalPages = Math.ceil(this.currentData.length / this.itemsPerPage);
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.renderPriceData();
        }
    }
    
    showLoading(show) {
        const spinner = document.getElementById('loadingSpinner');
        spinner.classList.toggle('d-none', !show);
    }
    
    showError(message) {
        const tbody = document.getElementById('priceDataTable');
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-4 text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </td>
            </tr>
        `;
    }
    
    startAutoRefresh() {
        this.stopAutoRefresh();
        this.autoRefreshInterval = setInterval(() => {
            this.loadPriceData();
        }, 30000); // Refresh every 30 seconds
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
    
    exportToCSV() {
        if (this.currentData.length === 0) {
            alert('No data to export');
            return;
        }
        
        const headers = ['ID', 'Symbol', 'Price', 'Bid', 'Ask', 'Volume', 'Timestamp'];
        const csvContent = [
            headers.join(','),
            ...this.currentData.map(record => [
                record.id,
                record.symbol,
                record.price,
                record.bid || '',
                record.ask || '',
                record.volume || '',
                record.timestamp
            ].join(','))
        ].join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `price_data_${new Date().getTime()}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    viewChart(symbol) {
        window.open(`/chart/${symbol}`, '_blank');
    }
    
    copyPrice(price) {
        navigator.clipboard.writeText(price).then(() => {
            // Show a toast or temporary message
            console.log('Price copied to clipboard:', price);
        });
    }
}

// Initialize the price data manager when the page loads
let priceDataManager;
document.addEventListener('DOMContentLoaded', () => {
    priceDataManager = new PriceDataManager();
});
