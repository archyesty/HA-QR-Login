/* qr-approve-panel — runs inside the authenticated HA frontend.
   Shows the display code for verification, lets permitted approvers
   pick which user to sign the device in as, and approves via WS. */

class QrApprovePanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) this._init();
  }

  async _init() {
    this._rendered = true;
    // Code travels in the path (/qr-approve/CODE) because the HA frontend
    // router reliably preserves paths but can strip query strings on load.
    const pathMatch = window.location.pathname.match(/qr-approve\/([^\/?#]+)/);
    this._code = pathMatch
      ? decodeURIComponent(pathMatch[1])
      : new URLSearchParams(window.location.search).get("code");
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:flex; justify-content:center; padding:32px 16px; font-family:var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
        .card { background:var(--card-background-color,#fff); color:var(--primary-text-color,#212121);
                border-radius:12px; box-shadow:var(--ha-card-box-shadow,0 2px 8px rgba(0,0,0,.15));
                padding:24px; max-width:420px; width:100%; }
        h2 { margin-top:0; }
        .display { font-size:1.8rem; letter-spacing:.3em; font-weight:700; text-align:center; margin:16px 0; }
        .hint { color:var(--secondary-text-color,#727272); font-size:.95rem; }
        select, button { width:100%; font-size:1rem; padding:12px; margin-top:12px; border-radius:8px; box-sizing:border-box; }
        button { border:none; cursor:pointer; }
        #approve { background:var(--primary-color,#03a9f4); color:#fff; }
        #deny { background:transparent; color:var(--error-color,#db4437); }
        .warn { color:var(--error-color,#db4437); font-size:.9rem; margin-top:8px; }
        .ok { text-align:center; font-size:1.2rem; padding:24px 0; }
      </style>
      <div class="card"><div id="body">Loading…</div></div>`;
    this._body = this.shadowRoot.getElementById("body");

    if (!this._code) { this._body.textContent = "No code in link."; return; }

    try {
      const info = await this._hass.callWS({ type: "qr_login/session_info", code: this._code });
      const { users } = await this._hass.callWS({ type: "qr_login/list_users" });
      this._render(info, users);
    } catch (e) {
      this._body.innerHTML = `<p>${e.message || "Code expired or you're not permitted to approve logins."}</p>`;
    }
  }

  _render(info, users) {
    const opts = users
      .sort((a, b) => (b.is_me ? 1 : 0) - (a.is_me ? 1 : 0))
      .map(u => `<option value="${u.id}" ${u.is_me ? "selected" : ""}>${u.name}${u.is_me ? " (you)" : ""}${u.is_admin ? " — admin" : ""}</option>`)
      .join("");
    this._body.innerHTML = `
      <h2>Approve sign-in?</h2>
      <p class="hint">Only approve if YOU just opened this on the device, and the code below matches its screen:</p>
      <div class="display">${info.display}</div>
      ${info.origin ? `<p class="hint" style="text-align:center">Device at: <b>${info.origin}</b></p>` : ""}
      <label class="hint">Sign the device in as:</label>
      <select id="target">${opts}</select>
      <div id="crosswarn" class="warn" style="display:none">Signing in a different user — that device will have their access.</div>
      <button id="approve">Approve</button>
      <button id="deny">Deny</button>`;
    const sel = this._body.querySelector("#target");
    const me = users.find(u => u.is_me);
    sel.addEventListener("change", () => {
      this._body.querySelector("#crosswarn").style.display = sel.value === (me && me.id) ? "none" : "block";
    });
    this._body.querySelector("#approve").addEventListener("click", () => this._approve(sel.value));
    this._body.querySelector("#deny").addEventListener("click", () => this._deny());
  }

  async _approve(userId) {
    try {
      const res = await this._hass.callWS({ type: "qr_login/approve", code: this._code, user_id: userId });
      this._body.innerHTML = `<div class="ok">✅ Device signed in as <b>${res.target}</b></div>`;
    } catch (e) {
      this._body.innerHTML = `<p>${e.message || "Approval failed."}</p>`;
    }
  }

  async _deny() {
    await this._hass.callWS({ type: "qr_login/deny", code: this._code });
    this._body.innerHTML = `<div class="ok">Denied.</div>`;
  }
}

customElements.define("qr-approve-panel", QrApprovePanel);
