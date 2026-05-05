import { useEffect, useRef } from "react";
import { useAppStore } from "../store/appStore";
import { WebSocketClient } from "../services/ws";

export function useWebSocket() {
  const handleWsMessage = useAppStore((s) => s.handleWsMessage);
  const setWsConnected = useAppStore((s) => s.setWsConnected);
  const clientRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    const client = new WebSocketClient("/ws/status", handleWsMessage, setWsConnected);
    clientRef.current = client;
    client.connect();

    return () => {
      client.disconnect();
    };
  }, [handleWsMessage, setWsConnected]);

  return clientRef;
}
