export const API_URL = process.env.REACT_APP_API_URL;
export const CHAT_URL = process.env.REACT_APP_CHAT_URL;

// socket.io-client treats the path segment of the connection URL as the
// namespace, not as the engine.io HTTP endpoint (that's always /socket.io
// unless overridden via the `path` option). When CHAT_URL is a relative
// prefix (prod, proxied by nginx under /chat/), that prefix has to be
// folded into the engine.io path explicitly, or the handshake request
// bypasses the proxy and silently hits the frontend's own SPA fallback.
export const CHAT_SOCKET_PATH = /^https?:\/\//i.test(CHAT_URL)
    ? '/socket.io'
    : `${CHAT_URL}/socket.io`;