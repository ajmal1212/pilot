import { request } from './client'

export const cloudflareApi = {
  get: () => request.get('cloudflare').json(),
  update: (data) => request.patch('cloudflare', { json: data }).json(),
  action: (action) => request.post('cloudflare/action', { json: { action } }).json(),
  create: (data) => request.post('cloudflare/create', { json: data }).json(),
  getSite: (name) => request.get(`cloudflare/sites/${name}`).json(),
  exposeSite: (name, expose, domain) => request.post(`cloudflare/sites/${name}/expose`, { json: { expose, domain } }).json(),
  delete: () => request.delete('cloudflare').json(),
  getZones: (apiToken) => request.get('cloudflare/zones', { searchParams: apiToken ? { api_token: apiToken } : {} }).json(),
}
