import { useEffect, useRef, useState } from "react";

export interface JobStatusEvent {
  event: string;
  job_id: string;
  job_type: string;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  workspace_id: string;
  result?: Record<string, any>;
  error?: string;
}

export function useWebSocket(
  workspaceId: string | null | undefined,
  token: string | null | undefined,
  onJobUpdate?: (event: JobStatusEvent) => void
) {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastEvent, setLastEvent] = useState<JobStatusEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!workspaceId || !token) {
      setIsConnected(false);
      return;
    }

    let retryCount = 0;
    const maxRetries = 5;

    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/v1/workspaces/${workspaceId}/jobs?token=${encodeURIComponent(
        token
      )}`;

      try {
        const socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          setIsConnected(true);
          retryCount = 0;
          pingIntervalRef.current = setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) {
              socket.send("ping");
            }
          }, 25000);
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === "job_status") {
              setLastEvent(data);
              if (onJobUpdate) {
                onJobUpdate(data);
              }
            }
          } catch {
            // Ignore ping/pong text frames
          }
        };

        socket.onerror = () => {
          setIsConnected(false);
        };

        socket.onclose = () => {
          setIsConnected(false);
          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
          }

          if (retryCount < maxRetries) {
            retryCount += 1;
            const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);
            reconnectTimeoutRef.current = setTimeout(connect, delay);
          }
        };
      } catch {
        setIsConnected(false);
      }
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [workspaceId, token, onJobUpdate]);

  return { isConnected, lastEvent };
}
