/* AnglerMap authentication adapter — Supabase Auth.
   Configuration is public project URL + anon/publishable key only.
   Never place the Supabase service_role key in this file. */
(() => {
  "use strict";
  const config = window.ANGLERMAP_SUPABASE || {};
  const configured = Boolean(config.url && config.anonKey && window.supabase?.createClient);
  const client = configured
    ? window.supabase.createClient(config.url, config.anonKey, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
      })
    : null;

  const statusText = (node, message, error = false) => {
    if (!node) return;
    node.textContent = message;
    node.style.color = error ? "#ffad9e" : "#9edbc4";
  };

  async function syncProfile(session) {
    if (!client || !session?.user) return;
    const local = (() => {
      try { return JSON.parse(localStorage.getItem("anglerMapUserProfileV1") || "null"); }
      catch (_) { return null; }
    })() || {};
    const payload = {
      user_id: session.user.id,
      display_name: local.name || session.user.user_metadata?.name || "",
      email: session.user.email || local.email || null,
      preferences: {
        role: local.role || "angler",
        experience: local.experience || "",
        communes: local.communes || [],
        categories: local.categories || [],
        species: local.species || [],
        techniques: local.techniques || []
      },
      updated_at: new Date().toISOString()
    };
    const { error } = await client.from("profiles").upsert(payload, { onConflict: "user_id" });
    if (error) throw error;
  }

  async function mountAuthPanel() {
    const modal = document.getElementById("amProfileModal");
    const body = modal?.querySelector(".profile-dialog-body");
    if (!body || body.querySelector("#amAuthPanel")) return;
    const panel = document.createElement("section");
    panel.id = "amAuthPanel";
    panel.style.cssText = "padding:14px;margin:0 0 15px;background:#102638;border:1px solid #35566a;border-radius:11px";
    panel.innerHTML = `
      <div style="font-weight:800;margin-bottom:5px">Cuenta AnglerMap</div>
      <div id="amAuthStatus" style="font-size:11px;color:#a9bdc8;margin-bottom:10px">${configured ? "Inicia sesión para sincronizar tu perfil y usarlo en otros dispositivos." : "Autenticación preparada. Falta conectar el proyecto Supabase para activar cuentas."}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <input id="amAuthPassword" type="password" minlength="8" autocomplete="current-password" placeholder="Contraseña (mín. 8)" style="min-width:0;padding:10px;background:#091b28;color:#edf5f8;border:1px solid #35566a;border-radius:8px">
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button type="button" id="amAuthSignIn" class="action-btn">Iniciar sesión</button>
          <button type="button" id="amAuthSignUp" class="action-btn primary">Crear cuenta</button>
        </div>
      </div>
      <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
        <button type="button" id="amAuthReset" class="action-btn">Recuperar contraseña</button>
        <button type="button" id="amAuthSignOut" class="action-btn" hidden>Cerrar sesión</button>
      </div>`;
    body.prepend(panel);
    const status = panel.querySelector("#amAuthStatus");
    const email = document.getElementById("amProfileEmail");
    const password = panel.querySelector("#amAuthPassword");
    const signIn = panel.querySelector("#amAuthSignIn");
    const signUp = panel.querySelector("#amAuthSignUp");
    const reset = panel.querySelector("#amAuthReset");
    const signOut = panel.querySelector("#amAuthSignOut");
    if (!configured) {
      [signIn, signUp, reset].forEach(button => button.disabled = true);
      return;
    }
    const run = async action => {
      const address = (email?.value || "").trim();
      if (!address) return statusText(status, "Ingresa primero tu correo electrónico.", true);
      try {
        if (action === "signup") {
          const name = document.getElementById("amProfileName")?.value?.trim() || "";
          const { data, error } = await client.auth.signUp({
            email: address, password: password.value,
            options: { data: { name }, emailRedirectTo: window.location.href.split("#")[0] }
          });
          if (error) throw error;
          if (data.session) await syncProfile(data.session);
          statusText(status, data.session
            ? "Cuenta creada y sesión iniciada. Perfil sincronizado."
            : "Cuenta creada. Revisa tu correo y confirma la dirección para activar el acceso.");
        } else if (action === "signin") {
          const { data, error } = await client.auth.signInWithPassword({ email: address, password: password.value });
          if (error) throw error;
          await syncProfile(data.session);
          statusText(status, "Sesión iniciada. Perfil sincronizado.");
          signOut.hidden = false;
        } else if (action === "reset") {
          const { error } = await client.auth.resetPasswordForEmail(address, { redirectTo: window.location.href.split("#")[0] });
          if (error) throw error;
          statusText(status, "Enviamos un enlace de recuperación si el correo está registrado.");
        }
      } catch (error) {
        statusText(status, error.message || "No se pudo completar la operación.", true);
      }
    };
    signIn.onclick = () => run("signin");
    signUp.onclick = () => {
      if ((password.value || "").length < 8) return statusText(status, "La contraseña debe tener al menos 8 caracteres.", true);
      run("signup");
    };
    reset.onclick = () => run("reset");
    signOut.onclick = async () => {
      const { error } = await client.auth.signOut();
      if (error) return statusText(status, error.message, true);
      signOut.hidden = true;
      statusText(status, "Sesión cerrada.");
    };
    const { data } = await client.auth.getSession();
    if (data.session) {
      statusText(status, "Sesión activa: " + (data.session.user.email || ""));
      signOut.hidden = false;
      try { await syncProfile(data.session); } catch (error) { statusText(status, "Sesión activa, pero no se pudo sincronizar el perfil: " + error.message, true); }
    }
    client.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" && session) {
        signOut.hidden = false;
        statusText(status, "Sesión activa: " + (session.user.email || ""));
      }
      if (event === "SIGNED_OUT") {
        signOut.hidden = true;
        statusText(status, "Sesión cerrada.");
      }
    });
    document.getElementById("amProfileForm")?.addEventListener("submit", async () => {
      const { data: current } = await client.auth.getSession();
      if (current.session) {
        try { await syncProfile(current.session); statusText(status, "Preferencias guardadas y sincronizadas."); }
        catch (error) { statusText(status, "No se pudo sincronizar: " + error.message, true); }
      }
    });
  }

  document.getElementById("userProfileBtn")?.addEventListener("click", () => {
    window.setTimeout(mountAuthPanel, 0);
  });
  if (client) {
    client.auth.getSession().then(({ data }) => {
      if (data.session) console.info("AnglerMap: sesión autenticada disponible.");
    });
  }
  window.AnglerMapAuth = {
    isConfigured: configured,
    getSession: () => client ? client.auth.getSession() : Promise.resolve({ data: { session: null }, error: null }),
    signOut: () => client ? client.auth.signOut() : Promise.reject(new Error("Supabase no está configurado."))
  };
})();
