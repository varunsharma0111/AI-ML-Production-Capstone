import React, { useEffect, useState } from "react";
import { request } from "../../services/apiClient";
import { HealthCheckResponse } from "../../types/api";
import { Badge } from "../ui/Badge";

export const HealthIndicator: React.FC = () => {
  const [status, setStatus] = useState<"ready" | "unavailable" | "checking">("checking");

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const res = await request<HealthCheckResponse>("/api/v1/system/status");
        if (isMounted) {
          setStatus(res.status === "ok" ? "ready" : "unavailable");
        }
      } catch {
        try {
          const res = await request<HealthCheckResponse>("/health/ready");
          if (isMounted) {
            setStatus(res.status === "ok" ? "ready" : "unavailable");
          }
        } catch {
          if (isMounted) {
            setStatus("unavailable");
          }
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  if (status === "checking") {
    return (
      <Badge variant="neutral" size="sm">
        <span className="spinner" style={{ width: "10px", height: "10px", marginRight: "0.25rem" }} />
        Checking Systems...
      </Badge>
    );
  }

  return (
    <Badge
      variant={status === "ready" ? "success" : "danger"}
      size="sm"
      icon={
        <span
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            backgroundColor: status === "ready" ? "var(--status-success)" : "var(--status-danger)",
            display: "inline-block",
            marginRight: "0.2rem",
          }}
        />
      }
    >
      {status === "ready" ? "Platform Systems Online" : "Service Degraded"}
    </Badge>
  );
};
