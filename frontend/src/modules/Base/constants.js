export const API_URL = process.env.REACT_APP_API_URL;
export const CHAT_URL = process.env.REACT_APP_CHAT_URL;

const CHAT_URL_IS_ABSOLUTE = /^https?:\/\//i.test(CHAT_URL);

// socket.io-client pulls two unrelated things out of what we hand it: the
// *namespace* comes from the pathname of the connection URI, while the
// actual HTTP endpoint it polls/upgrades is always /socket.io unless
// overridden via the `path` option. In prod, CHAT_URL is a relative proxy
// prefix ("/chat") that nginx strips before forwarding to node — it must
// only ever land in `path`, never in the connection URI, or it gets
// misread as part of the namespace and silently connects to a namespace
// nobody's listening on (no errors, messages just vanish).
export const CHAT_SOCKET_PATH = CHAT_URL_IS_ABSOLUTE
    ? '/socket.io'
    : `${CHAT_URL}/socket.io`;

// Build the connection URI for a given namespace (e.g. "/chat-1"). In dev,
// CHAT_URL is an absolute host (http://localhost:4000) reached directly, so
// it belongs in the URI. In prod it must be left out of the URI entirely —
// a bare "/chat-1" makes socket.io-client connect to the current page's own
// origin automatically, whatever that origin is. See CHAT_SOCKET_PATH above.
export const chatSocketUrl = (namespace) =>
    CHAT_URL_IS_ABSOLUTE ? `${CHAT_URL}${namespace}` : namespace;