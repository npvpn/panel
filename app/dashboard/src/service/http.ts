import { FetchOptions, $fetch as ohMyFetch } from "ofetch";
import { getAuthToken } from "utils/authStorage";

export const $fetch = ohMyFetch.create({
  baseURL: import.meta.env.VITE_BASE_API,
  onRequest({ request, options }) {
    const method = (options.method || "GET").toString();
    const url = typeof request === "string" ? request : (request as any)?.url;
    const headers = { ...(options.headers || {}) } as Record<string, any>;
    if (headers["Authorization"]) headers["Authorization"] = "***";
    // Prefer `query` but show `params` if used
    const query = (options as any).query || (options as any).params;
    // Avoid logging binary bodies
    const body =
      typeof (options as any).body === "string" ||
      typeof (options as any).body === "object"
        ? (options as any).body
        : typeof (options as any).body;
    // eslint-disable-next-line no-console
    console.debug("[HTTP request]", {
      method,
      url,
      baseURL: import.meta.env.VITE_BASE_API,
      query,
      body,
      headers,
    });
  },
  onRequestError({ request, options, error }) {
    const url = typeof request === "string" ? request : (request as any)?.url;
    const method = (options.method || "GET").toString();
    const headers = { ...(options.headers || {}) } as Record<string, any>;
    if (headers["Authorization"]) headers["Authorization"] = "***";
    // eslint-disable-next-line no-console
    console.debug("[HTTP request error]", {
      method,
      url,
      baseURL: import.meta.env.VITE_BASE_API,
      error: String(error),
      headers,
    });
  },
  onResponse({ request, options, response }) {
    const url = typeof request === "string" ? request : (request as any)?.url;
    const method = (options.method || "GET").toString();
    // eslint-disable-next-line no-console
    console.debug("[HTTP response]", {
      method,
      url,
      status: response.status,
    });
  },
  onResponseError({ request, options, response }) {
    const url = typeof request === "string" ? request : (request as any)?.url;
    const method = (options.method || "GET").toString();
    // eslint-disable-next-line no-console
    console.debug("[HTTP response error]", {
      method,
      url,
      status: response?.status,
    });
  },
});

export const fetcher = <T = any>(
  url: string,
  ops: FetchOptions<"json"> = {}
) => {
  const token = getAuthToken();
  if (token) {
    ops["headers"] = {
      ...(ops?.headers || {}),
      Authorization: `Bearer ${getAuthToken()}`,
    };
  }
  return $fetch<T>(url, ops);
};

export const fetch = fetcher;
