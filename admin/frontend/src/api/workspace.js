import { request, unwrap } from './client'

export const workspaceApi = {
  apps: () => unwrap(request.get('workspace/apps').json()),
  tree: (appName) => unwrap(request.get(`workspace/tree/${appName}`).json()),
  getFile: (appName, path) => unwrap(request.get(`workspace/file/${appName}`, { searchParams: { path } }).json()),
  saveFile: (appName, path, content) => unwrap(request.post(`workspace/file/${appName}`, { json: { path, content } }).json()),
}
