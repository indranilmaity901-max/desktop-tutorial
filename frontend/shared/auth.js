export function token() {
  return sessionStorage.getItem("wpacs_token") || "";
}

export function setSession(auth) {
  sessionStorage.setItem("wpacs_token", auth.access_token);
  sessionStorage.setItem("wpacs_user", JSON.stringify(auth.user));
}

export function user() {
  return JSON.parse(sessionStorage.getItem("wpacs_user") || "null");
}

export function logout() {
  sessionStorage.removeItem("wpacs_token");
  sessionStorage.removeItem("wpacs_user");
  window.location.href = "/frontend/index.html";
}
