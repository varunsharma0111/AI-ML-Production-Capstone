import { describe, expect, it, vi } from "vitest";
import { ApiError, request } from "../services/apiClient";

describe("apiClient", () => {
  it("injects Authorization header and X-Request-ID", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "ok" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const result = await request<{ status: string }>("/api/v1/test", { token: "my_token_123" });

    expect(result).toEqual({ status: "ok" });
    expect(mockFetch).toHaveBeenCalledOnce();

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1].headers as Headers;

    expect(headers.get("Authorization")).toBe("Bearer my_token_123");
    expect(headers.get("X-Request-ID")).toBeTruthy();
  });

  it("parses RFC-7807 problem details on non-2xx responses", async () => {
    const problemPayload = {
      type: "https://ai-ml-production-capstone.dev/problems/permission_denied",
      title: "Forbidden",
      status: 403,
      detail: "You do not have permission to perform this action.",
      code: "permission_denied",
      request_id: "req_xyz789",
    };

    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => problemPayload,
    });
    vi.stubGlobal("fetch", mockFetch);

    await expect(request("/api/v1/workspaces/w1/tasks")).rejects.toThrow(ApiError);

    try {
      await request("/api/v1/workspaces/w1/tasks");
    } catch (err) {
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(403);
      expect(apiErr.code).toBe("permission_denied");
      expect(apiErr.requestId).toBe("req_xyz789");
    }
  });
});
