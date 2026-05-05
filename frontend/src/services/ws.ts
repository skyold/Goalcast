import type { WsMessage } from "../types";

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private onMessage: (msg: WsMessage) => void;
  private onStatusChange: (connected: boolean) => void;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    url: string,
    onMessage: (msg: WsMessage) => void,
    onStatusChange: (connected: boolean) => void,
  ) {
    this.url = url;
    this.onMessage = onMessage;
    this.onStatusChange = onStatusChange;
  }

  connect() {
    if (this.ws) return;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}${this.url}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.onStatusChange(true);
    };

    this.ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data);
        this.onMessage(msg);
      } catch {
        console.warn("[WS] Failed to parse message:", event.data);
      }
    };

    this.ws.onclose = () => {
      this.onStatusChange(false);
      this.ws = null;
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.onStatusChange(false);
  }
}
