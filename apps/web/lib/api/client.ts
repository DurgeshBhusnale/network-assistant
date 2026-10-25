import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

/**
 * Typed API client. Requests go to /api/* on the web origin; Next.js rewrites them to the
 * FastAPI service, so the phone needs only one origin and there is no CORS.
 */
export const api = createClient<paths>({ baseUrl: "/api" });

export type Schemas = components["schemas"];
