import { useRef, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { FileText, SlidersHorizontal, ShieldCheck } from "lucide-react";
import { api } from "../shared/api";
import { Button, FeatureUnavailable, Notice } from "../shared/ui";
import { UploadPage } from "../features/upload";
import { ProfilesPage, ProfileEditorPage } from "../features/profiles";
import { ReviewPage } from "../features/review";

export function App() {
  const cache = useQueryClient();
  const [code, setCode] = useState("");
  const codeInput = useRef<HTMLInputElement>(null);
  const [loginError, setLoginError] = useState<
    "credentials" | "network" | null
  >(null);
  const [submitting, setSubmitting] = useState(false);
  const session = useQuery({
    queryKey: ["session"],
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/auth/session");
      if (error) throw new Error("Session unavailable");
      return data.data;
    },
  });
  const capabilities = useQuery({
    queryKey: ["capabilities"],
    enabled: !!session.data,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/capabilities");
      if (error) throw new Error("Capabilities unavailable");
      return data.data;
    },
  });
  async function login(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setLoginError(null);
    try {
      const { error } = await api.POST("/api/v1/auth/login", {
        body: { accessCode: code },
      });
      if (error) {
        setLoginError(
          error.error.code === "UNAUTHENTICATED" ? "credentials" : "network",
        );
        codeInput.current?.focus();
      } else {
        setCode("");
        await cache.invalidateQueries({ queryKey: ["session"] });
      }
    } catch {
      setLoginError("network");
    } finally {
      setSubmitting(false);
    }
  }
  return (
    <>
      <a className="skip-link" href="#main-content">
        Preskočiť na obsah
      </a>
      {session.data?.mode === "fixture" && (
        <div className="fixture-banner" role="status">
          Ukážkový režim · Syntetické údaje · Zápis do eGrantu je vypnutý
        </div>
      )}
      <header className="masthead">
        <NavLink to="/documents" className="wordmark">
          eGrant<span> / dokumenty</span>
        </NavLink>
        <span className="human-review">
          <ShieldCheck size={18} aria-hidden="true" /> Ľudská kontrola
        </span>
      </header>
      {session.isPending ? (
        <main id="main-content" tabIndex={-1}>
          <Notice>Načítavame pracovný priestor…</Notice>
        </main>
      ) : session.isError ? (
        <main id="main-content" tabIndex={-1} className="login">
          <p className="eyebrow">Súkromný pracovný priestor</p>
          <h1>Prihlásenie</h1>
          <p>Na prístup k dokumentom zadajte prístupový kód.</p>
          <form onSubmit={login}>
            <label htmlFor="access-code">Prístupový kód</label>
            <input
              ref={codeInput}
              id="access-code"
              type="password"
              autoComplete="current-password"
              value={code}
              aria-invalid={loginError === "credentials"}
              aria-describedby={
                loginError ? "access-help access-error" : "access-help"
              }
              onChange={(event) => setCode(event.target.value)}
              required
            />
            <p id="access-help" className="field-help">
              Kód vám poskytne správca pracovného priestoru.
            </p>
            {loginError && (
              <p id="access-error" className="field-error" role="alert">
                {loginError === "credentials"
                  ? "Prístupový kód nie je správny. Skúste ho zadať znova."
                  : "Server nie je dostupný. Skontrolujte pripojenie a skúste znova."}
              </p>
            )}
            <Button type="submit" disabled={submitting}>
              {submitting ? "Prihlasujeme…" : "Prihlásiť sa"}
            </Button>
          </form>
        </main>
      ) : (
        <div className="layout">
          <nav aria-label="Hlavná navigácia">
            <p className="eyebrow">Spracovanie</p>
            <NavLink to="/documents">
              <FileText size={19} aria-hidden="true" /> Dokumenty
            </NavLink>
            <NavLink to="/profiles">
              <SlidersHorizontal size={19} aria-hidden="true" /> Profily
            </NavLink>
            <div className="provider-status">
              <p className="eyebrow">Integrácie</p>
              {capabilities.isPending ? (
                <p>Načítavame stav…</p>
              ) : capabilities.isError ? (
                <p role="alert">Stav sa nepodarilo načítať.</p>
              ) : (
                <>
                  <p>
                    OCR ·{" "}
                    {capabilities.data.ocrConfigured
                      ? "Dostupné"
                      : "Nedostupné"}
                  </p>
                  <p>
                    AI ·{" "}
                    {capabilities.data.aiConfigured ? "Dostupné" : "Nedostupné"}
                  </p>
                  <p>
                    eGrant ·{" "}
                    {capabilities.data.egrantConfigured
                      ? "Dostupné"
                      : "Nedostupné"}
                  </p>
                </>
              )}
            </div>
          </nav>
          <main id="main-content" tabIndex={-1}>
            <Routes>
              <Route path="/documents" element={<UploadPage />} />
              <Route path="/profiles" element={<ProfilesPage />} />
              <Route path="/profiles/new" element={<ProfileEditorPage />} />
              <Route path="/profiles/:id" element={<ProfileEditorPage />} />
              <Route path="/review/:extractionId" element={<ReviewPage />} />
              <Route
                path="/submissions/:id"
                element={<FeatureUnavailable title="Export a odoslanie" />}
              />
              <Route path="*" element={<Navigate to="/documents" replace />} />
            </Routes>
          </main>
        </div>
      )}
      <footer>Dokument → Návrh údajov → Vaša kontrola → Potvrdenie</footer>
    </>
  );
}
