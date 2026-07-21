import { request, unwrap } from './client'

export const terminalApi = {
  createSession: () => unwrap(request.post('terminal/session').json()),
  sendInput: (sessionId, hexData) => unwrap(request.post(`terminal/input/${sessionId}`, { json: { data: hexData } }).json()),
  resize: (sessionId, cols, rows) => unwrap(request.post(`terminal/resize/${sessionId}`, { json: { cols, rows } }).json()),
  // SSE endpoint helper URL
  getStreamUrl: (sessionId) => {
    // Determine the base API URL prefix from client configuration
    const apiRoot = '/api/v1'
    return `${apiRoot}/terminal/stream/${sessionId}`
  }
}
