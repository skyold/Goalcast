export const shouldIgnoreSocketClose = (
  closedSocket: WebSocket,
  currentSocket: WebSocket | null,
) => currentSocket !== closedSocket

export const getWebSocketUrl = () => {
  if (import.meta.env.PROD) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/chat`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.hostname || 'localhost'
  return `${protocol}//${host}:8000/ws/chat`
}
