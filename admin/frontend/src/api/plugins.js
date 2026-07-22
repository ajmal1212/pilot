import { request } from './client'

export const pluginsApi = {
  list: () => request.get('plugins').json(),
  install: (data) => request.post('plugins/install', { json: data }).json(),
  update: (name) => request.post('plugins/update', { json: { name } }).json(),
  uninstall: (name) => request.post('plugins/uninstall', { json: { name } }).json(),
}
