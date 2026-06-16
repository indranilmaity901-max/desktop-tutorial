import { setSession } from "../../shared/auth.js";

document.querySelector("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const response = await fetch("/api/v2/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: form.get("username"),
      password: form.get("password"),
      role: "AGENT"
    })
  });
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    document.querySelector("#result").textContent = payload.detail || payload.message;
    return;
  }
  setSession(payload.data);
  window.location.href = "/frontend/agent/pages/dashboard.html";
});
