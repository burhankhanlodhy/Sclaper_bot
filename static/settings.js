class SettingsManager {
    constructor() {
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadDatabaseStats();
        this.loadConfiguration();
    }
    
    bindEvents() {
        // Configuration save button
        document.getElementById('saveConfigBtn').addEventListener('click', () => {
            this.saveConfiguration();
        });
        
        // Database stats refresh
        document.getElementById('refreshStatsBtn').addEventListener('click', () => {
            this.loadDatabaseStats();
        });
        
        // Export data button
        document.getElementById('exportDataBtn').addEventListener('click', () => {
            this.exportData();
        });
        
        // Reset confirmation inputs
        document.getElementById('confirmTradeReset').addEventListener('input', (e) => {
            const button = document.getElementById('resetTradesBtn');
            button.disabled = e.target.value !== 'RESET TRADES';
        });
        
        document.getElementById('confirmFullReset').addEventListener('input', (e) => {
            const button = document.getElementById('resetAllBtn');
            button.disabled = e.target.value !== 'RESET ALL';
        });
        
        // Reset buttons
        document.getElementById('resetTradesBtn').addEventListener('click', () => {
            this.resetTrades();
        });
        
        document.getElementById('resetAllBtn').addEventListener('click', () => {
            this.resetAll();
        });
    }
    
    async loadConfiguration() {
        try {
            const response = await fetch('/api/config');
            const result = await response.json();
            
            if (result.success) {
                const config = result.data;
                document.getElementById('initialBalance').value = config.initial_balance || 10000;
                document.getElementById('maxRiskPerTrade').value = config.max_risk_per_trade || 2;
                document.getElementById('updateInterval').value = config.update_interval || 5;
                document.getElementById('enableNotifications').checked = config.enable_notifications !== false;
            }
        } catch (error) {
            console.error('Error loading configuration:', error);
            this.showMessage('Error loading configuration', 'danger');
        }
    }
    
    async saveConfiguration() {
        try {
            const config = {
                initial_balance: parseFloat(document.getElementById('initialBalance').value),
                max_risk_per_trade: parseFloat(document.getElementById('maxRiskPerTrade').value),
                update_interval: parseInt(document.getElementById('updateInterval').value),
                enable_notifications: document.getElementById('enableNotifications').checked
            };
            
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('Configuration saved successfully', 'success');
            } else {
                this.showMessage('Failed to save configuration: ' + result.error, 'danger');
            }
        } catch (error) {
            console.error('Error saving configuration:', error);
            this.showMessage('Error saving configuration', 'danger');
        }
    }
    
    async loadDatabaseStats() {
        try {
            const response = await fetch('/api/database-stats');
            const result = await response.json();
            
            if (result.success) {
                const stats = result.data;
                document.getElementById('totalTradesCount').textContent = stats.total_trades || 0;
                document.getElementById('totalPriceRecords').textContent = stats.total_price_records || 0;
                document.getElementById('databaseSize').textContent = this.formatBytes(stats.database_size || 0);
            }
        } catch (error) {
            console.error('Error loading database stats:', error);
            document.getElementById('totalTradesCount').textContent = 'Error';
            document.getElementById('totalPriceRecords').textContent = 'Error';
            document.getElementById('databaseSize').textContent = 'Error';
        }
    }
    
    async exportData() {
        try {
            this.showMessage('Preparing data export...', 'info');
            
            const response = await fetch('/api/export-data', {
                method: 'POST'
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `kraken-bot-data-${new Date().toISOString().split('T')[0]}.zip`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showMessage('Data exported successfully', 'success');
            } else {
                const result = await response.json();
                this.showMessage('Failed to export data: ' + result.error, 'danger');
            }
        } catch (error) {
            console.error('Error exporting data:', error);
            this.showMessage('Error exporting data', 'danger');
        }
    }
    
    async resetTrades() {
        if (!confirm('Are you sure you want to reset all trading data? This cannot be undone.')) {
            return;
        }
        
        const button = document.getElementById('resetTradesBtn');
        const spinner = button.querySelector('.loading-spinner');
        
        try {
            button.disabled = true;
            spinner.style.display = 'inline';
            
            const response = await fetch('/api/reset-trades', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('Trading data reset successfully', 'success');
                document.getElementById('confirmTradeReset').value = '';
                this.loadDatabaseStats();
            } else {
                this.showMessage('Failed to reset trading data: ' + result.error, 'danger');
            }
        } catch (error) {
            console.error('Error resetting trades:', error);
            this.showMessage('Error resetting trading data', 'danger');
        } finally {
            button.disabled = true; // Keep disabled until confirmation text is entered again
            spinner.style.display = 'none';
        }
    }
    
    async resetAll() {
        if (!confirm('Are you ABSOLUTELY sure you want to reset EVERYTHING? This will delete all data and cannot be undone.')) {
            return;
        }
        
        const button = document.getElementById('resetAllBtn');
        const spinner = button.querySelector('.loading-spinner');
        
        try {
            button.disabled = true;
            spinner.style.display = 'inline';
            
            const response = await fetch('/api/reset-all', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('All data reset successfully. Redirecting to dashboard...', 'success');
                document.getElementById('confirmFullReset').value = '';
                
                // Redirect to dashboard after a short delay
                setTimeout(() => {
                    window.location.href = '/';
                }, 3000);
            } else {
                this.showMessage('Failed to reset all data: ' + result.error, 'danger');
            }
        } catch (error) {
            console.error('Error resetting all data:', error);
            this.showMessage('Error resetting all data', 'danger');
        } finally {
            button.disabled = true; // Keep disabled until confirmation text is entered again
            spinner.style.display = 'none';
        }
    }
    
    showMessage(message, type) {
        const container = document.getElementById('statusMessages');
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        container.appendChild(alertDiv);
        
        // Auto-remove success messages after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }
    
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize settings manager when page loads
document.addEventListener('DOMContentLoaded', function() {
    new SettingsManager();
});
