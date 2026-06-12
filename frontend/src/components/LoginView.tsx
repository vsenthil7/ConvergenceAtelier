import { useEffect, useState } from "react";
import { Input } from "@progress/kendo-react-inputs";
import { Button } from "@progress/kendo-react-buttons";
import { getAuthConfig, type AuthConfig } from "../lib/auth";
import { useAuth } from "../lib/AuthContext";

interface Props {
  fetchImpl?: typeof fetch;
  /** Injectable hook so tests can simulate a Google credential without GIS. */
  onRequestGoogle?: () => Promise<string>;
}

/** Seeded demo accounts (all share the seeded demo password). One-tap sign-in. */
const DEMO_PASSWORD = "Atelier!2026";
const DEMO_ACCOUNTS: ReadonlyArray<{ email: string; label: string; testid: string }> = [
  { email: "super@atelier.demo", label: "Super admin", testid: "demo-super" },
  { email: "admin@react-summit.demo", label: "Tenant admin", testid: "demo-admin" },
  { email: "user@react-summit.demo", label: "Attendee", testid: "demo-user" },
];

export function LoginView({ fetchImpl = fetch, onRequestGoogle }: Props) {
  const { login, loginWithGoogle, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [config, setConfig] = useState<AuthConfig | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAuthConfig(fetchImpl)
      .then((c) => {
        if (!cancelled) setConfig(c);
      })
      .catch(() => {
        if (!cancelled) setConfig({ google_enabled: false, google_client_id: "" });
      });
    return () => {
      cancelled = true;
    };
  }, [fetchImpl]);

  const submit = async () => {
    setSubmitting(true);
    try {
      await login(email, password);
    } catch {
      // error surfaced via context
    } finally {
      setSubmitting(false);
    }
  };

  /** One-tap demo sign-in: fill the fields (so the user sees who they are) and
   *  authenticate immediately, without ever exposing the shared password. */
  const signInAsDemo = async (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword(DEMO_PASSWORD);
    setSubmitting(true);
    try {
      await login(demoEmail, DEMO_PASSWORD);
    } catch {
      // error surfaced via context
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogle = async () => {
    if (!onRequestGoogle) return;
    setSubmitting(true);
    try {
      const idToken = await onRequestGoogle();
      await loginWithGoogle(idToken);
    } catch {
      // error surfaced via context
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-view">
      <div className="login-card">
        <h1>Convergence Atelier</h1>
        <p className="login-sub">Sign in to your organiser workspace</p>

        <label>
          Email
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(String(e.value))}
            aria-label="login-email"
            autoComplete="username"
          />
        </label>

        <label>
          Password
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(String(e.value))}
            aria-label="login-password"
            autoComplete="current-password"
          />
        </label>

        {error && (
          <p role="alert" data-testid="login-error" className="login-error">
            {error}
          </p>
        )}

        <Button
          themeColor="primary"
          onClick={() => void submit()}
          disabled={submitting || !email || !password}
          data-testid="login-submit"
        >
          Sign in
        </Button>

        {config?.google_enabled && (
          <Button
            fillMode="outline"
            onClick={() => void handleGoogle()}
            disabled={submitting}
            data-testid="login-google"
          >
            Continue with Google
          </Button>
        )}

        <div className="login-demo">
          <strong>Demo accounts</strong>
          <p className="login-demo-hint">
            One-tap sign-in — no password needed.
          </p>
          <div className="login-demo-buttons">
            {DEMO_ACCOUNTS.map((acct) => (
              <Button
                key={acct.email}
                fillMode="outline"
                onClick={() => void signInAsDemo(acct.email)}
                disabled={submitting}
                data-testid={acct.testid}
                title={acct.email}
              >
                {acct.label}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
