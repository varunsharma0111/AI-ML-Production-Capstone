import { ProblemDetails } from "../types/api";

export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly requestId: string;
  public readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail || problem.title || "An API error occurred");
    this.name = "ApiError";
    this.status = problem.status;
    this.code = problem.code;
    this.requestId = problem.request_id;
    this.problem = problem;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  token?: string | null;
  body?: any;
}

function generateRequestId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "req_" + Math.random().toString(36).substring(2, 11);
}

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { token, headers: customHeaders, body, ...fetchOptions } = options;

  const baseUrl = (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_URL) ? import.meta.env.VITE_API_URL : "";
  const targetUrl = endpoint.startsWith('/') ? `${baseUrl}${endpoint}` : endpoint;

  const headers = new Headers(customHeaders);
  headers.set("Accept", "application/json");
  headers.set("X-Request-ID", generateRequestId());

  let processedBody: BodyInit | null = null;
  if (body) {
    if (body instanceof FormData || body instanceof Blob || typeof body === "string") {
      processedBody = body;
    } else {
      headers.set("Content-Type", "application/json");
      processedBody = JSON.stringify(body);
    }
  }

  if (token && token !== "null" && token !== "undefined" && token.trim() !== "") {
    headers.set("Authorization", `Bearer ${token.trim()}`);
  }

  const response = await fetch(targetUrl, {
    ...fetchOptions,
    body: processedBody,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }

    let problem: ProblemDetails;
    try {
      problem = await response.json();
    } catch {
      problem = {
        type: "about:blank",
        title: response.statusText || "HTTP Error",
        status: response.status,
        detail: `Request failed with status ${response.status}`,
        code: "http_error",
        request_id: headers.get("X-Request-ID") || "unknown",
      };
    }
    throw new ApiError(problem);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
