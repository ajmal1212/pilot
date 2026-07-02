import { request } from './client'

export const appsApi = {
  marketplace: () => request.get('apps/marketplace').json(),
  installed: () => request.get('apps/').json(),
  fetchUpdates: () => request.post('apps/fetch').json(),
  updateSource: (name, payload) => request.post(`apps/${encodeURIComponent(name)}/update-source`, { json: payload }).json(),
}
