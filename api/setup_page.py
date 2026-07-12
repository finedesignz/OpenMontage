"""The /setup page: paste a Claude subscription token to authorize the agent.

Deliberately a single self-contained page with no build step and no framework.
The API key is never stored in the page — it is typed once, held in memory for
the fetch, and sent as X-API-Key.
"""

from __future__ import annotations

SETUP_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenMontage · Authorize agent</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; display: grid; place-items: center;
    background: #0b0d10; color: #e8eaed; padding: 32px;
    font: 15px/1.55 ui-sans-serif, -apple-system, "Segoe UI", system-ui, sans-serif;
  }
  main { width: 100%; max-width: 560px; }
  h1 { font-size: 20px; margin: 0 0 4px; letter-spacing: -0.01em; }
  .sub { color: #9aa3ad; margin: 0 0 28px; }
  .card { background: #14171c; border: 1px solid #23282f; border-radius: 12px; padding: 22px; }
  label { display: block; font-weight: 600; font-size: 13px; margin: 0 0 6px; }
  .hint { color: #9aa3ad; font-size: 13px; margin: 0 0 8px; }
  input, textarea {
    width: 100%; background: #0b0d10; color: #e8eaed; border: 1px solid #2c323a;
    border-radius: 8px; padding: 10px 12px; font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 13px; resize: vertical;
  }
  input:focus, textarea:focus { outline: 2px solid #4c8dff; outline-offset: -1px; border-color: transparent; }
  .field + .field { margin-top: 18px; }
  code { background: #0b0d10; border: 1px solid #2c323a; border-radius: 5px; padding: 1px 6px; font-size: 12.5px; }
  button {
    margin-top: 22px; width: 100%; padding: 11px; border: 0; border-radius: 8px;
    background: #4c8dff; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer;
  }
  button:hover { background: #3f7ceb; }
  button:disabled { opacity: .55; cursor: default; }
  .status { margin-top: 18px; padding: 11px 13px; border-radius: 8px; font-size: 13.5px; display: none; }
  .status.show { display: block; }
  .ok { background: #10281a; border: 1px solid #1f5c39; color: #7ee2a8; }
  .err { background: #2a1416; border: 1px solid #6b2b30; color: #ff9ba3; }
  .state { margin-bottom: 20px; font-size: 13.5px; color: #9aa3ad; }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px; background: #6b7480; }
  .dot.live { background: #3ddc84; }
</style>
</head>
<body>
<main>
  <h1>Authorize the OpenMontage agent</h1>
  <p class="sub">Every render is driven by a headless Claude Code agent inside this container. It needs your credentials to run.</p>

  <div class="state"><span class="dot" id="dot"></span><span id="state">Checking current status…</span></div>

  <div class="card">
    <div class="field">
      <label for="key">API key</label>
      <p class="hint">The <code>OPENMONTAGE_API_KEYS</code> value for this deployment. Not stored — used only to authorize this request.</p>
      <input id="key" type="password" autocomplete="off" placeholder="••••••••••••••••">
    </div>

    <div class="field">
      <label for="token">Claude subscription token</label>
      <p class="hint">On any machine where you are logged in to Claude Code, run <code>claude setup-token</code> and paste the result here.</p>
      <textarea id="token" rows="4" autocomplete="off" placeholder="sk-ant-oat01-…"></textarea>
    </div>

    <button id="go">Authorize agent</button>
    <div class="status" id="status"></div>
  </div>
</main>

<script>
const $ = (id) => document.getElementById(id);

function say(msg, ok) {
  const s = $("status");
  s.textContent = msg;
  s.className = "status show " + (ok ? "ok" : "err");
}

function paintState(data) {
  const live = data.configured;
  $("dot").className = "dot" + (live ? " live" : "");
  if (!live) {
    $("state").textContent = "Not authorized — the agent cannot run jobs yet.";
  } else if (data.source === "oauth_token") {
    const when = data.updated_at ? new Date(data.updated_at).toLocaleString() : "unknown time";
    $("state").textContent = "Authorized with a Claude subscription token, set " + when + ".";
  } else {
    $("state").textContent = "Authorized with an ANTHROPIC_API_KEY from the environment.";
  }
}

async function refresh() {
  try {
    const r = await fetch("/v1/auth/status");
    paintState(await r.json());
  } catch {
    $("state").textContent = "Could not reach the API.";
  }
}

$("go").addEventListener("click", async () => {
  const key = $("key").value.trim();
  const token = $("token").value.trim();
  if (!key) return say("Enter the API key for this deployment.", false);
  if (!token) return say("Paste the token from `claude setup-token`.", false);

  $("go").disabled = true;
  try {
    const r = await fetch("/v1/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": key },
      body: JSON.stringify({ token }),
    });
    const data = await r.json().catch(() => ({}));
    if (r.ok) {
      $("token").value = "";
      say("Agent authorized. New jobs will use this token.", true);
      paintState(data);
    } else if (r.status === 401) {
      say("That API key was rejected.", false);
    } else {
      say(data.detail || ("Failed with HTTP " + r.status), false);
    }
  } catch (e) {
    say("Request failed: " + e.message, false);
  } finally {
    $("go").disabled = false;
  }
});

refresh();
</script>
</body>
</html>
"""
