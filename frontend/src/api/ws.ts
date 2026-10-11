import { BACKEND_ORIGIN } from './client';

type EventHandler = (data: any) => void;

export class SessionWebSocket {
  private sessionId: string;
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private isDestroyed = false;
  private pingInterval: any = null;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
    this.connect();
  }

  private connect() {
    if (this.isDestroyed) return;

    let baseWsOrigin = '';
    if (BACKEND_ORIGIN) {
      if (BACKEND_ORIGIN.startsWith('https://')) {
        baseWsOrigin = BACKEND_ORIGIN.replace(/^https:\/\//, 'wss://');
      } else if (BACKEND_ORIGIN.startsWith('http://')) {
        baseWsOrigin = BACKEND_ORIGIN.replace(/^http:\/\//, 'ws://');
      } else {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        baseWsOrigin = `${protocol}//${BACKEND_ORIGIN.replace(/^\/+/, '')}`;
      }
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      baseWsOrigin = `${protocol}//${window.location.host}`;
    }

    const token = localStorage.getItem('bst_token');
    const query = token ? `?token=${encodeURIComponent(token)}` : '';
    const url = `${baseWsOrigin}/ws/sessions/${this.sessionId}${query}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.emit('connection_status', { status: 'connected' });
        // Start ping interval
        if (this.pingInterval) clearInterval(this.pingInterval);
        this.pingInterval = setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send('ping');
          }
        }, 15000);
      };

      this.ws.onmessage = (event) => {
        if (event.data === 'pong') return;
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.event) {
            this.emit(parsed.event, parsed.data);
          }
        } catch {
          // ignore non-json
        }
      };

      this.ws.onclose = () => {
        this.emit('connection_status', { status: 'disconnected' });
        if (this.pingInterval) clearInterval(this.pingInterval);
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        if (this.ws) {
          this.ws.close();
        }
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.isDestroyed) return;
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 10000);
      setTimeout(() => this.connect(), delay);
    }
  }

  public on(event: string, handler: EventHandler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  public off(event: string, handler: EventHandler) {
    if (this.handlers.has(event)) {
      this.handlers.get(event)!.delete(handler);
    }
  }

  private emit(event: string, data: any) {
    const eventHandlers = this.handlers.get(event);
    if (eventHandlers) {
      eventHandlers.forEach((h) => h(data));
    }
  }

  public destroy() {
    this.isDestroyed = true;
    if (this.pingInterval) clearInterval(this.pingInterval);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.handlers.clear();
  }
}
