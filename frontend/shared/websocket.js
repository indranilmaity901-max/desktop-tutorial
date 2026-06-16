import { api } from "./utils.js";


export function connectLive(onMessage) {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${scheme}//${window.location.host}/api/v2/live`);
  socket.onmessage = (event) => onMessage(JSON.parse(event.data || "{}"));
  return socket;
}

export async function refreshOnLive(load) {
  connectLive(async (message) => {
    if (["agent_status", "workstation_event", "productivity"].includes(message.type)) {
      await load();
    }
  });
}
