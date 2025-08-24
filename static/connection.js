// Global WebSocket connection manager shared by all pages
(function() {
  if (window.GlobalConnection) return; // Singleton guard

  class GlobalConnectionManager {
    constructor() {
      this.ws = null;
      this.status = 'connecting';
      this.reconnectAttempts = 0;
      this.maxReconnectDelay = 10000; // cap backoff at 10s
      this.heartbeatTimer = null;
      this.connect();
      document.addEventListener('DOMContentLoaded', () => this.updateStatusBadge());
    }

    get wsUrl() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}/ws`;
    }

    connect() {
      try {
        this.setStatus('connecting');
        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
          this.reconnectAttempts = 0;
          this.setStatus('connected');
          this.startHeartbeat();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            // Fan out to listeners on the window
            window.dispatchEvent(new CustomEvent('ws:update', { detail: data }));
          } catch (e) {
            console.error('WS parse error:', e);
          }
        };

        this.ws.onclose = () => {
          this.stopHeartbeat();
          this.setStatus('disconnected');
          this.scheduleReconnect();
        };

        this.ws.onerror = () => {
          this.setStatus('error');
        };
      } catch (e) {
        console.error('WS connect error:', e);
        this.setStatus('error');
        this.scheduleReconnect();
      }
    }

    scheduleReconnect() {
      this.reconnectAttempts += 1;
      const delay = Math.min(1000 * this.reconnectAttempts, this.maxReconnectDelay);
      setTimeout(() => this.connect(), delay);
    }

    startHeartbeat() {
      this.stopHeartbeat();
      this.heartbeatTimer = setInterval(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }));
        }
      }, 30000);
    }

    stopHeartbeat() {
      if (this.heartbeatTimer) {
        clearInterval(this.heartbeatTimer);
        this.heartbeatTimer = null;
      }
    }

    setStatus(status) {
      this.status = status;
      this.updateStatusBadge();
    }

    updateStatusBadge() {
      const el = document.getElementById('connectionStatus');
      if (!el) return;
      const map = {
        connected: { text: 'Connected', cls: 'bg-success', icon: 'fa-circle' },
        disconnected: { text: 'Disconnected', cls: 'bg-danger', icon: 'fa-circle' },
        connecting: { text: 'Connecting...', cls: 'bg-warning', icon: 'fa-circle' },
        error: { text: 'Error', cls: 'bg-danger', icon: 'fa-exclamation-circle' }
      };
      const cfg = map[this.status] || map.connecting;
      el.className = `badge ${cfg.cls}`;
      el.innerHTML = `<i class="fas ${cfg.icon}"></i> ${cfg.text}`;
    }

    send(obj) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(obj));
      }
    }
  }

  window.GlobalConnection = new GlobalConnectionManager();
})();
