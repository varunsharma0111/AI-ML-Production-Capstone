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
        const res = await request<HealthCheckResponse>("/health/ready");
        if (isMounted) {
          setStatus(res.status === "ok" ? "ready" : "unavailable");
        }
      } catch {
        if (isMounted) {
          setStatus("unavailable");
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Poll health every 30s
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  if (status === "checking") {
    return <Badge variant="neutral">System Checking...</Badge>;
  }

  return (
    <Badge variant={status === "ready" ? "online" : "offline"}>
      Backend API: {status === "ready" ? "Healthy (200)" : "Degraded (503)"}
    </Badge>
  );
};
