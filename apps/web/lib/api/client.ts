import createClient, { type Middleware } from "openapi-fetch";

import { accessToken } from "@/lib/auth/supabase";

import type { components, paths } from "./schema";

/** Sends the Supabase access token with every API call. */
const authMiddleware: Middleware = {
  async onRequest({ request }) {
    const token = await accessToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
};

/**
 * Typed API client. Requests go to /api/* on the web origin; Next.js rewrites them to the
 * FastAPI service, so the phone needs only one origin and there is no CORS.
 */
export const api = createClient<paths>({ baseUrl: "/api" });
api.use(authMiddleware);

export type Schemas = components["schemas"];

export type ApiErrorBody = Schemas["ErrorResponse"];

/** Thrown by hooks so screens can show the server's message and branch on its code. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export function toApiError(status: number, body: unknown): ApiError {
  if (typeof body === "object" && body !== null && "error" in body) {
    const { code, message } = (body as ApiErrorBody).error;
    return new ApiError(status, code, message);
  }
  return new ApiError(status, "HTTP_ERROR", "Something went wrong. Please try again.");
}

/** Unwraps an openapi-fetch result: data, or a typed ApiError. */
export async function unwrap<T>(
  promise: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await promise;
  if (error !== undefined || data === undefined) throw toApiError(response.status, error);
  return data;
}
