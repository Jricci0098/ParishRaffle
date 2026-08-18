import { useEffect, useRef } from "react";

export interface WsMessage {
  event: string;
  data: Record<string, unknown>;
  ts?: string;
}

interface Options {
  /** Register this device with the admin panel. */
  deviceName?: string;
  role?: string;
  /** Called for every event received. */
  onEvent?: (msg: WsMessage) => void;
}

/**
 * Resilient WebSocket connection with auto-reconnect and heartbeat. Works on a
 * local network with no Internet. Returns nothing; callers react via onEvent.
 */
export function useWebSocket({ deviceName, role, onEvent }: Options) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let heartbeat: ReturnType<typeof setInterval> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${window.location.host}/ws`);

      ws.onopen = () => {
        if (deviceName) {
          ws?.send(
            JSON.stringify({
              action: "register",
              name: deviceName,
              role: role || "viewer",
            })
          );
        }
        heartbeat = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "heartbeat" }));
          }
        }, 10000);
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as WsMessage;
          onEventRef.current?.(msg);
        } catch {
          /* ignore malformed */
        }
      };

      ws.onclose = () => {
        if (heartbeat) clearInterval(heartbeat);
        if (!closed) {
          reconnectTimer = setTimeout(connect, 2000);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      closed = true;
      if (heartbeat) clearInterval(heartbeat);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deviceName, role]);
}
