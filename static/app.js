class TradingDashboard {
    constructor() {
        this.ws = null; // Not used directly; rely on GlobalConnection
        
        this.init();
    }
    
    init() {
        this.bindToGlobalConnection();
        this.bindEvents();
        this.loadInitialData();
    }
    
    bindToGlobalConnection() {
        // Use GlobalConnection for updates
        window.addEventListener('ws:update', (e) => {
            const data = e.detail;
            this.handleWebSocketMessage(data);
        });
        // On load, reflect current status
        if (window.GlobalConnection) {
            // Update badge once in case DOM loaded after init
            setTimeout(() => window.GlobalConnection.updateStatusBadge(), 0);
        }
    }
    
    handleWebSocketMessage(data) {
        if (data.type === 'update') {
            this.updatePortfolio(data.portfolio);
            this.updateTradingStatus(data.is_trading);
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }
    }
    
    bindEvents() {
        // Close all positions button
    const cap = document.getElementById('closeAllPositions');
    if (cap) cap.addEventListener('click', () => { this.closeAllPositions(); });
        
        // Auto-refresh data every 30 seconds
        setInterval(() => {
            this.loadOpenTrades();
            this.loadTradeHistory();
        }, 30000);
    }
    
    async loadInitialData() {
        await Promise.all([
            this.loadPortfolio(),
            this.loadOpenTrades(),
            this.loadTradeHistory(),
            this.loadTradingPairs()
        ]);
    }
    
    async loadPortfolio() {
        try {
            const response = await fetch('/api/portfolio');
            const result = await response.json();
            
            if (result.success) {
                this.updatePortfolio(result.data);
            }
        } catch (error) {
            console.error('Error loading portfolio:', error);
        }
    }
    
    updatePortfolio(portfolio) {
        if (!portfolio) return;
        
        document.getElementById('totalBalance').textContent = `$${(portfolio.total_balance || 100).toFixed(2)}`;
        document.getElementById('availableBalance').textContent = `$${(portfolio.available_balance || 100).toFixed(2)}`;
        document.getElementById('totalEquity').textContent = `$${(portfolio.total_equity || 100).toFixed(2)}`;
        
        const totalPnL = portfolio.total_profit_loss || 0;
        const pnlElement = document.getElementById('totalPnL');
        pnlElement.textContent = `$${totalPnL.toFixed(2)}`;
        pnlElement.className = totalPnL >= 0 ? 'profit-positive' : 'profit-negative';
        
        const winRate = portfolio.win_rate || 0;
        document.getElementById('winRate').textContent = `${winRate.toFixed(1)}%`;
        
        document.getElementById('totalTrades').textContent = portfolio.total_trades || 0;
        document.getElementById('openTrades').textContent = portfolio.open_trades_count || 0;
        document.getElementById('closedTrades').textContent = portfolio.closed_trades_count || 0;
    }
    
    async loadOpenTrades() {
        try {
            const response = await fetch('/api/open-trades');
            const result = await response.json();
            
            if (result.success) {
                this.updateOpenTrades(result.data);
            }
        } catch (error) {
            console.error('Error loading open trades:', error);
        }
    }
    
    updateOpenTrades(trades) {
        const tbody = document.getElementById('openPositionsTable');
        
        if (trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No open positions</td></tr>';
            return;
        }
        
        tbody.innerHTML = trades.map(trade => `
            <tr>
                <td><strong>${trade.symbol}</strong></td>
                <td><span class="badge ${trade.trade_type === 'BUY' ? 'bg-success' : 'bg-danger'}">${trade.trade_type}</span></td>
                <td>$${parseFloat(trade.entry_price).toFixed(4)}</td>
                <td>${parseFloat(trade.quantity).toFixed(6)}</td>
                <td class="profit-positive">-</td>
                <td>$${parseFloat(trade.stop_loss_price).toFixed(4)}</td>
                <td>$${parseFloat(trade.take_profit_price).toFixed(4)}</td>
                <td>${new Date(trade.entry_time).toLocaleString()}</td>
            </tr>
        `).join('');
    }
    
    async loadTradeHistory() {
        try {
            const response = await fetch('/api/trades?limit=20');
            const result = await response.json();
            
            if (result.success) {
                this.updateTradeHistory(result.data);
            }
        } catch (error) {
            console.error('Error loading trade history:', error);
        }
    }
    
    updateTradeHistory(trades) {
        const tbody = document.getElementById('tradeHistoryTable');
        
        if (trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No trades yet</td></tr>';
            return;
        }
        
        tbody.innerHTML = trades.slice(0, 10).map(trade => {
            const pnl = trade.profit_loss || 0;
            return `
                <tr>
                    <td><strong>${trade.symbol}</strong></td>
                    <td><span class="badge ${trade.trade_type === 'BUY' ? 'bg-success' : 'bg-danger'}">${trade.trade_type}</span></td>
                    <td>$${parseFloat(trade.entry_price).toFixed(4)}</td>
                    <td>${trade.exit_price ? '$' + parseFloat(trade.exit_price).toFixed(4) : '-'}</td>
                    <td>${parseFloat(trade.quantity).toFixed(6)}</td>
                    <td class="${pnl >= 0 ? 'profit-positive' : 'profit-negative'}">$${pnl.toFixed(2)}</td>
                    <td><span class="badge ${trade.status === 'CLOSED' ? 'bg-success' : trade.status === 'OPEN' ? 'bg-warning' : 'bg-danger'}">${trade.status}</span></td>
                    <td>${new Date(trade.entry_time).toLocaleString()}</td>
                    <td>${trade.exit_time ? new Date(trade.exit_time).toLocaleString() : '-'}</td>
                </tr>
            `;
        }).join('');
    }
    
    async loadTradingPairs() {
        try {
            const response = await fetch('/api/pairs');
            const result = await response.json();
            
            if (result.success) {
                this.updateTradingPairs(result.data);
            }
        } catch (error) {
            console.error('Error loading trading pairs:', error);
        }
    }
    
    updateTradingPairs(pairs) {
        const container = document.getElementById('tradingPairs');
        
        if (pairs.length === 0) {
            container.innerHTML = '<small class="text-muted">No pairs loaded</small>';
            return;
        }
        
        container.innerHTML = pairs.slice(0, 10).map(pair => 
            `<div class="d-flex justify-content-between align-items-center mb-1">
                <small><strong>${pair.symbol}</strong></small>
                <small class="text-muted">${pair.base_currency}/USD</small>
            </div>`
        ).join('');
    }
    
    updateTradingStatus(isRunning) {
        const status = document.getElementById('tradingStatus');
        if (status) {
            if (isRunning) {
                status.textContent = 'Running';
            status.className = 'badge bg-success';
            } else {
                status.textContent = 'Stopped';
            status.className = 'badge bg-warning';
        }
        }
    }
    
    async closeAllPositions() {
        if (!confirm('Are you sure you want to close all open positions?')) {
            return;
        }
        
        try {
            const button = document.getElementById('closeAllPositions');
            button.disabled = true;
            button.innerHTML = '<div class="spinner"></div> Closing...';
            
            const response = await fetch('/api/close-all-positions', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                alert('All positions closed successfully');
                this.loadOpenTrades();
                this.loadPortfolio();
            } else {
                alert('Error closing positions: ' + result.error);
            }
        } catch (error) {
            console.error('Error closing positions:', error);
            alert('Error closing positions');
        } finally {
            const button = document.getElementById('closeAllPositions');
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-times-circle me-2"></i>Close All Positions';
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new TradingDashboard();
});
