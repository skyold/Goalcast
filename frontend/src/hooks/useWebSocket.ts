import { useEffect, useRef } from "react";
import { useAppStore } from "../store/appStore";
import type { WsEvent } from "../types";

export function useWebSocket() {
  const handleWsEvent = useAppStore((s) => s.handleWsEvent);
  const setWsConnected = useAppStore((s) => s.setWsConnected);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/events`);
      wsRef.current = ws;

      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => {
        setWsConnected(false);
        reconnectRef.current = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (e: MessageEvent) => {
        try {
          const event = JSON.parse(e.data as string) as WsEvent;
          handleWsEvent(event);
        } catch {
          /* ignore malformed messages */
        }
      };
    }

    connect();

    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [handleWsEvent, setWsConnected]);
}
