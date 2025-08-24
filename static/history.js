class TradingHistory {
    constructor() {
        this.currentPage = 1;
        this.tradesPerPage = 50;
        this.allTrades = [];
        this.filteredTrades = [];
        this.currentFilter = 'all'; // 'all', 'closed', 'open'
        
        this.init();
    }
    
    init() {
    this.bindEvents();
    // Ensure initial load happens even if some optional elements are missing
    this.loadTradeHistory();
        this.loadPortfolioSummary();
        this.bindToGlobalConnection();
    }
    
    bindToGlobalConnection() {
        window.addEventListener('ws:update', (e) => {
            const data = e.detail;
            if (data.type === 'update') {
                this.updateTradingStatus(data.is_trading);
            }
        });
        if (window.GlobalConnection) {
            setTimeout(() => window.GlobalConnection.updateStatusBadge(), 0);
        }
    }
    
    updateTradingStatus(isRunning) {
    const button = document.getElementById('toggleTrading');
    if (!button) return; // Not shown on this page
        
        if (isRunning) {
            button.innerHTML = '<i class="fas fa-pause"></i> Stop Trading';
            button.className = 'btn btn-outline-danger btn-sm';
        } else {
            button.innerHTML = '<i class="fas fa-play"></i> Start Trading';
            button.className = 'btn btn-outline-success btn-sm';
        }
    }
    
    bindEvents() {
        // Filter buttons
    const allBtn = document.getElementById('allTradesBtn');
    const closedBtn = document.getElementById('closedTradesBtn');
    const openBtn = document.getElementById('openTradesBtn');
    if (allBtn) allBtn.addEventListener('click', () => this.setFilter('all'));
    if (closedBtn) closedBtn.addEventListener('click', () => this.setFilter('closed'));
    if (openBtn) openBtn.addEventListener('click', () => this.setFilter('open'));
        
        // Filter inputs
    const symbolFilter = document.getElementById('symbolFilter');
    const statusFilter = document.getElementById('statusFilter');
    const typeFilter = document.getElementById('tradeTypeFilter');
    const clearBtn = document.getElementById('clearFilters');
    if (symbolFilter) symbolFilter.addEventListener('input', () => this.applyFilters());
    if (statusFilter) statusFilter.addEventListener('change', () => this.applyFilters());
    if (typeFilter) typeFilter.addEventListener('change', () => this.applyFilters());
    if (clearBtn) clearBtn.addEventListener('click', () => this.clearFilters());
        
        // Action buttons
    const refreshBtn = document.getElementById('refreshBtn');
    const exportBtn = document.getElementById('exportBtn');
    const toggleBtn = document.getElementById('toggleTrading');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadTradeHistory());
    if (exportBtn) exportBtn.addEventListener('click', () => this.exportToCSV());
    if (toggleBtn) toggleBtn.addEventListener('click', () => this.toggleTrading());
    }
    
    setFilter(filter) {
        this.currentFilter = filter;
        
        // Update button states
        document.querySelectorAll('.btn-group .btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (filter === 'all') {
            document.getElementById('allTradesBtn').classList.add('active');
        } else if (filter === 'closed') {
            document.getElementById('closedTradesBtn').classList.add('active');
        } else if (filter === 'open') {
            document.getElementById('openTradesBtn').classList.add('active');
        }
        
        this.loadTradeHistory();
    }
    
    async loadTradeHistory() {
        try {
            let endpoint = '/api/trades?limit=1000';
            
            if (this.currentFilter === 'closed') {
                endpoint = '/api/closed-trades?limit=1000';
            } else if (this.currentFilter === 'open') {
                endpoint = '/api/open-trades';
            }
            
            const response = await fetch(endpoint);
            const result = await response.json();
            
            if (result.success) {
                this.allTrades = result.data;
                this.applyFilters();
                this.calculateAndUpdateSummary(); // Update summary cards after loading trades
            } else {
                console.error('Error loading trades:', result.error);
                this.showError('Failed to load trade history');
            }
        } catch (error) {
            console.error('Error loading trade history:', error);
            this.showError('Failed to load trade history');
        }
    }
    
    async loadPortfolioSummary() {
        try {
            // Calculate summary from loaded trades
            this.calculateAndUpdateSummary();
        } catch (error) {
            console.error('Error loading portfolio summary:', error);
        }
    }
    
    calculateAndUpdateSummary() {
        const totalTrades = this.allTrades.length;
        
        const closedTrades = this.allTrades.filter(trade => 
            trade.status === 'CLOSED' || trade.status === 'closed'
        );
        
        const openTrades = this.allTrades.filter(trade => 
            trade.status === 'OPEN' || trade.status === 'open'
        );
        
        const winningTrades = closedTrades.filter(trade => {
            const pnl = parseFloat(trade.profit_loss || trade.pnl || 0);
            return pnl > 0;
        });
        
        const losingTrades = closedTrades.filter(trade => {
            const pnl = parseFloat(trade.profit_loss || trade.pnl || 0);
            return pnl < 0;
        });
        
        const totalPnL = closedTrades.reduce((sum, trade) => {
            return sum + parseFloat(trade.profit_loss || trade.pnl || 0);
        }, 0);
        
        // Update the cards
        document.getElementById('totalTradesCount').textContent = totalTrades;
        document.getElementById('winningTradesCount').textContent = winningTrades.length;
        document.getElementById('losingTradesCount').textContent = losingTrades.length;
        
        const pnlElement = document.getElementById('totalProfitLoss');
        pnlElement.textContent = `$${totalPnL.toFixed(2)}`;
        
        // Update card colors based on P&L
        const pnlCard = pnlElement.closest('.card');
        if (totalPnL > 0) {
            pnlCard.className = 'card bg-success text-white';
        } else if (totalPnL < 0) {
            pnlCard.className = 'card bg-danger text-white';
        } else {
            pnlCard.className = 'card bg-info text-white';
        }
    }
    
    applyFilters() {
        let filtered = [...this.allTrades];
        
        // Symbol filter
        const symbolFilter = document.getElementById('symbolFilter').value.trim();
        if (symbolFilter) {
            filtered = filtered.filter(trade => 
                trade.symbol.toLowerCase().includes(symbolFilter.toLowerCase())
            );
        }
        
        // Status filter
        const statusFilter = document.getElementById('statusFilter').value;
        if (statusFilter) {
            filtered = filtered.filter(trade => trade.status === statusFilter);
        }
        
        // Trade type filter
        const typeFilter = document.getElementById('tradeTypeFilter').value;
        if (typeFilter) {
            filtered = filtered.filter(trade => trade.trade_type === typeFilter);
        }
        
        this.filteredTrades = filtered;
        this.currentPage = 1;
        this.displayTrades();
        this.updatePagination();
    }
    
    clearFilters() {
        document.getElementById('symbolFilter').value = '';
        document.getElementById('statusFilter').value = '';
        document.getElementById('tradeTypeFilter').value = '';
        this.applyFilters();
    }
    
    displayTrades() {
        const tbody = document.getElementById('historyTable');
        
        if (this.filteredTrades.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="12" class="text-center text-muted">
                        <i class="fas fa-info-circle me-2"></i>No trades found
                    </td>
                </tr>
            `;
            return;
        }
        
        const startIndex = (this.currentPage - 1) * this.tradesPerPage;
        const endIndex = startIndex + this.tradesPerPage;
        const pageTrades = this.filteredTrades.slice(startIndex, endIndex);
        
        tbody.innerHTML = pageTrades.map(trade => {
            const pnl = trade.profit_loss || 0;
            const entryTime = new Date(trade.entry_time).toLocaleString();
            const exitTime = trade.exit_time ? new Date(trade.exit_time).toLocaleString() : '-';
            
            return `
                <tr>
                    <td><span class="badge bg-secondary">#${trade.id}</span></td>
                    <td><strong>${trade.symbol}</strong></td>
                    <td>
                        <span class="badge ${trade.trade_type === 'BUY' ? 'bg-success' : 'bg-danger'}">
                            ${trade.trade_type}
                        </span>
                    </td>
                    <td>${parseFloat(trade.quantity).toFixed(6)}</td>
                    <td>$${parseFloat(trade.entry_price).toFixed(4)}</td>
                    <td>${trade.exit_price ? '$' + parseFloat(trade.exit_price).toFixed(4) : '-'}</td>
                    <td>$${parseFloat(trade.trade_amount).toFixed(2)}</td>
                    <td>$${parseFloat(trade.fees).toFixed(2)}</td>
                    <td class="${pnl >= 0 ? 'text-success' : 'text-danger'}">
                        <strong>$${pnl.toFixed(2)}</strong>
                    </td>
                    <td>
                        <span class="badge ${this.getStatusBadgeClass(trade.status)}">
                            ${trade.status}
                        </span>
                    </td>
                    <td><small>${entryTime}</small></td>
                    <td><small>${exitTime}</small></td>
                </tr>
            `;
        }).join('');
    }
    
    getStatusBadgeClass(status) {
        switch (status) {
            case 'OPEN': return 'bg-warning';
            case 'CLOSED': return 'bg-success';
            case 'STOPPED': return 'bg-danger';
            default: return 'bg-secondary';
        }
    }
    
    updatePagination() {
        const totalPages = Math.ceil(this.filteredTrades.length / this.tradesPerPage);
        const pagination = document.getElementById('pagination');
        
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }
        
    let paginationHTML = '';
        
        // Previous button
        paginationHTML += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="tradeHistory.goToPage(${this.currentPage - 1}); return false;">Previous</a>
            </li>
        `;
        
        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                paginationHTML += `
                    <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="tradeHistory.goToPage(${i}); return false;">${i}</a>
                    </li>
                `;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                paginationHTML += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }
        
        // Next button
        paginationHTML += `
            <li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="tradeHistory.goToPage(${this.currentPage + 1}); return false;">Next</a>
            </li>
        `;
        
        pagination.innerHTML = paginationHTML;
    }
    
    goToPage(page) {
        const totalPages = Math.ceil(this.filteredTrades.length / this.tradesPerPage);
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.displayTrades();
            this.updatePagination();
        }
    }
    
    exportToCSV() {
        if (this.filteredTrades.length === 0) {
            alert('No trades to export');
            return;
        }
        
        const headers = [
            'ID', 'Symbol', 'Type', 'Quantity', 'Entry Price', 'Exit Price',
            'Amount', 'Fees', 'P&L', 'Status', 'Entry Time', 'Exit Time'
        ];
        
        const csvContent = [
            headers.join(','),
            ...this.filteredTrades.map(trade => [
                trade.id,
                trade.symbol,
                trade.trade_type,
                trade.quantity,
                trade.entry_price,
                trade.exit_price || '',
                trade.trade_amount,
                trade.fees,
                trade.profit_loss || 0,
                trade.status,
                trade.entry_time,
                trade.exit_time || ''
            ].join(','))
        ].join('\\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `trading_history_${new Date().toISOString().split('T')[0]}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
    
    async toggleTrading() {
        try {
            const button = document.getElementById('toggleTrading');
            button.disabled = true;
            
            const response = await fetch('/api/toggle-trading', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                this.updateTradingStatus(result.status === 'started');
            } else {
                alert('Error toggling trading: ' + result.error);
            }
        } catch (error) {
            console.error('Error toggling trading:', error);
            alert('Error toggling trading');
        } finally {
            document.getElementById('toggleTrading').disabled = false;
        }
    }
    
    showError(message) {
        const tbody = document.getElementById('historyTable');
        tbody.innerHTML = `
            <tr>
                <td colspan="12" class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>${message}
                </td>
            </tr>
        `;
    }
}

// Expose instance globally for inline handlers
window.tradeHistory = null;
document.addEventListener('DOMContentLoaded', () => {
    window.tradeHistory = new TradingHistory();
});
