import { token } from "./auth.js";


export async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token()}`,
      ...(options.headers || {})
    }
  });
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.detail || payload.message || "Request failed");
  }
  return payload.data;
}

export function fmtDate(value) {
  return value ? new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value)) : "No event";
}

export function minutes(value) {
  const total = Number(value || 0);
  const hours = Math.floor(total / 60);
  const rest = total % 60;
  return hours ? `${hours}h ${String(rest).padStart(2, "0")}m` : `${rest}m`;
}
