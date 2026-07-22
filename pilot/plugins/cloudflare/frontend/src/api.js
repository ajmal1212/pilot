const API_V1_PREFIX = '/api/v1'

async function call(method, path, body) {
  const res = await fetch(`${API_V1_PREFIX}/${path}`, {
    method,
    credentials: 'same-origin',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  return res.json()
}

export function apiErrorMessage(payload, fallback = 'Request failed.') {
  const error = payload?.error
  if (typeof error?.message === 'string' && error.message) return error.message
  if (typeof error === 'string' && error) return error
  return fallback
}

export const cloudflareApi = {
  get: () => call('GET', 'cloudflare'),
  update: (data) => call('PATCH', 'cloudflare', data),
  action: (action) => call('POST', 'cloudflare/action', { action }),
  create: (data) => call('POST', 'cloudflare/create', data),
  getSite: (name) => call('GET', `cloudflare/sites/${name}`),
  exposeSite: (name, expose, domain) => call('POST', `cloudflare/sites/${name}/expose`, { expose, domain }),
  delete: () => call('DELETE', 'cloudflare'),
  getZones: (apiToken) => call('POST', 'cloudflare/zones', apiToken ? { api_token: apiToken } : {}),
  startLogin: () => call('POST', 'cloudflare/login/start'),
  getLoginStatus: () => call('GET', 'cloudflare/login/status'),
  cancelLogin: () => call('POST', 'cloudflare/login/cancel'),
  disconnectLogin: () => call('POST', 'cloudflare/login/disconnect'),
  getSsh: () => call('GET', 'cloudflare/ssh'),
  configureSsh: (enable, hostname) => call('POST', 'cloudflare/ssh', { enable, hostname }),
}
