/**
 * Minimal fetch client. Auth is an HttpOnly cookie; on a 401 we try one
 * refresh (rotating the refresh token) and replay the request.
 */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

type Query = Record<string, string | number | boolean | null | undefined>

function url(path: string, query?: Query): string {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
  }
  const qs = params.toString()
  return `/api/v1${path}${qs ? `?${qs}` : ''}`
}

let refreshing: Promise<boolean> | null = null

async function refresh(): Promise<boolean> {
  refreshing ??= fetch(url('/auth/refresh'), { method: 'POST', credentials: 'include' })
    .then((r) => r.ok)
    .finally(() => setTimeout(() => (refreshing = null), 0))
  return refreshing
}

export async function api<T>(
  path: string,
  options: { method?: string; query?: Query; body?: unknown; retry?: boolean } = {},
): Promise<T> {
  const { method = 'GET', query, body, retry = true } = options
  const response = await fetch(url(path, query), {
    method,
    credentials: 'include',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (response.status === 401 && retry && !path.startsWith('/auth/')) {
    if (await refresh()) return api<T>(path, { ...options, retry: false })
  }
  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = await response.json()
      detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail)
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}
