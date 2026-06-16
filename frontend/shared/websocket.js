import { token } from "./auth.js";


export function connectLive(onMessage, onDisconnect) {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${scheme}//${window.location.host}/api/v2/live?token=${encodeURIComponent(token())}`);
  socket.onmessage = (event) => onMessage(JSON.parse(event.data || "{}"));
  socket.onclose = () => onDisconnect?.();
  return socket;
}

export async function refreshOnLive(load, pollMs = 10000) {
  let polling = null;
  const startPolling = () => {
    if (polling) {
      return;
    }
    polling = window.setInterval(load, pollMs);
  };
  const socket = connectLive(async (message) => {
    if (["agent_status", "workstation_event", "productivity"].includes(message.type)) {
      await load();
    }
  }, startPolling);
  socket.onerror = startPolling;
  return socket;
}
