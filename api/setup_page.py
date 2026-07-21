"""Operator-facing HTML: the login view and the agent-authorization view.

Two self-contained pages, no build step, no framework. Server-supplied values
are only ever written via textContent (never innerHTML) and the operator email
is HTML-escaped where it is interpolated into markup, so neither page is an XSS
sink.
"""

from __future__ import annotations

from html import escape

_STYLE = """
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
  .topbar { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }
  .who { font-size: 12.5px; color: #9aa3ad; }
  .who a { color: #6ea2ff; text-decoration: none; margin-left: 10px; }
"""

# --- Login view -------------------------------------------------------------

LOGIN_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenMontage · Sign in</title>
<style>%STYLE%</style>
</head>
<body>
<main>
  <h1>Sign in to OpenMontage</h1>
  <p class="sub">Enter your operator email. We'll send a one-time magic link - no password.</p>
  <div class="card">
    <div class="field">
      <label for="email">Email</label>
      <p class="hint">Only authorised operator addresses can sign in.</p>
      <input id="email" type="email" autocomplete="email" placeholder="you@example.com">
    </div>
    <button id="go">Send magic link</button>
    <div class="status" id="status"></div>
  </div>
</main>
<script>
const $ = (id) => document.getElementById(id);
function say(msg, ok) {
  const s = $("status"); s.textContent = msg;
  s.className = "status show " + (ok ? "ok" : "err");
}
$("go").addEventListener("click", async () => {
  const email = $("email").value.trim();
  if (!email) return say("Enter your email.", false);
  $("go").disabled = true;
  try {
    const r = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    if (r.ok) {
      say("Check your inbox - if that address is authorised, a sign-in link is on its way.", true);
    } else {
      const d = await r.json().catch(() => ({}));
      say(d.detail || ("Failed with HTTP " + r.status), false);
    }
  } catch (e) {
    say("Request failed: " + e.message, false);
  } finally {
    $("go").disabled = false;
  }
});
</script>
</body>
</html>
""".replace("%STYLE%", _STYLE)


# --- Setup-unavailable view (Titanium not wired) ----------------------------

SETUP_UNAVAILABLE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenMontage · Setup unavailable</title>
<style>%STYLE%</style>
</head>
<body>
<main>
  <h1>Setup is not available yet</h1>
  <p class="sub">Operator sign-in runs through Titanium Licensing, which is not wired on this deployment.</p>
  <div class="card">
    <p class="hint">Set <code>TITANIUM_APP_ID</code> and <code>TITANIUM_RETURN_URL</code> in the
    deployment environment, then redeploy. Once the portal is wired, this page becomes the
    magic-link sign-in for authorizing the agent.</p>
  </div>
</main>
</body>
</html>""".replace("%STYLE%", _STYLE)


# --- Token / authorize-agent view -------------------------------------------

_SETUP_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenMontage · Authorize agent</title>
<style>%STYLE%</style>
</head>
<body>
<main>
  <div class="topbar">
    <h1>Authorize the OpenMontage agent</h1>
    <span class="who">%WHO%</span>
  </div>
  <p class="sub">Every render is driven by a headless Claude Code agent inside this container. It needs your Claude subscription to run.</p>

  <div class="state"><span class="dot" id="dot"></span><span id="state">Checking current status...</span></div>

  <div class="card">
    <div class="field">
      <label for="token">Claude subscription token</label>
      <p class="hint">On any machine where you are logged in to Claude Code, run <code>claude setup-token</code> and paste the result here.</p>
      <textarea id="token" rows="4" autocomplete="off" placeholder="sk-ant-oat01-..."></textarea>
    </div>
    <button id="go">Authorize agent</button>
    <div class="status" id="status"></div>
  </div>
</main>
<script>
const $ = (id) => document.getElementById(id);
function say(msg, ok) {
  const s = $("status"); s.textContent = msg;
  s.className = "status show " + (ok ? "ok" : "err");
}
function paintState(data) {
  const live = data.configured;
  $("dot").className = "dot" + (live ? " live" : "");
  if (!live) {
    $("state").textContent = "Not authorized - the agent cannot run jobs yet.";
  } else {
    const when = data.updated_at ? new Date(data.updated_at).toLocaleString() : "unknown time";
    $("state").textContent = "Authorized on your Claude subscription since " + when + ".";
  }
}
async function refresh() {
  try { paintState(await (await fetch("/v1/auth/status")).json()); }
  catch { $("state").textContent = "Could not reach the API."; }
}
$("go").addEventListener("click", async () => {
  const token = $("token").value.trim();
  if (!token) return say("Paste the token from `claude setup-token`.", false);
  $("go").disabled = true;
  try {
    const r = await fetch("/v1/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const data = await r.json().catch(() => ({}));
    if (r.ok) {
      $("token").value = "";
      say("Token verified against Anthropic. The agent runs on your subscription and stays authorized across redeploys.", true);
      paintState(data);
    } else if (r.status === 401) {
      say("Your session has expired - reload and sign in again.", false);
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
""".replace("%STYLE%", _STYLE)


def render_setup(operator_email: str | None) -> str:
    """Render the authorize-agent page. `operator_email` shows who is signed in."""
    if operator_email:
        who = f"{escape(operator_email)} · <a href=\"/auth/logout\" id=\"logout\">Sign out</a>"
    else:
        who = ""
    html = _SETUP_TEMPLATE.replace("%WHO%", who)
    # A logout link must POST (state-changing); rewrite the anchor to do so.
    if operator_email:
        html = html.replace(
            "</script>\n</body>",
            "document.getElementById('logout')?.addEventListener('click', (e) => {"
            " e.preventDefault();"
            " const f = document.createElement('form'); f.method='POST'; f.action='/auth/logout';"
            " document.body.appendChild(f); f.submit(); });\n</script>\n</body>",
        )
    return html
