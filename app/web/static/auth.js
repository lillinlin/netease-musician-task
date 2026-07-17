const $ = (s) => document.querySelector(s);
const changeMode = location.pathname === "/change-password";

function showChange(current = "") {
  $("#login-panel").classList.add("hidden");
  $("#change-panel").classList.remove("hidden");
  $("#current-password").value = current;
  $("#new-password").focus();
}

async function request(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "操作失败");
  return data;
}

function fail(error) {
  $("#auth-error").textContent = error.message || String(error);
}

$("#auth-login").addEventListener("click", async () => {
  const password = $("#auth-password").value;
  try {
    const data = await request("/api/auth/login", { password });
    if (data.must_change_password) showChange(password);
    else location.href = "/";
  } catch (error) { fail(error); }
});

$("#auth-change").addEventListener("click", async () => {
  const current_password = $("#current-password").value;
  const new_password = $("#new-password").value;
  if (new_password !== $("#confirm-password").value) return fail(new Error("两次输入的新密码不一致"));
  try {
    await request("/api/auth/change-password", { current_password, new_password });
    location.href = "/";
  } catch (error) { fail(error); }
});

for (const input of document.querySelectorAll("input")) {
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") (changeMode || !$("#change-panel").classList.contains("hidden") ? $("#auth-change") : $("#auth-login")).click();
  });
}

if (changeMode) showChange();
