import { useMemo, useState } from "react";
import { AppBar, AppBarSection, AppBarSpacer } from "@progress/kendo-react-layout";
import { Button } from "@progress/kendo-react-buttons";
import { Loader } from "@progress/kendo-react-indicators";
import { AuthProvider, useAuth, type TokenStore } from "./lib/AuthContext";
import { makeAuthedFetch } from "./lib/authedFetch";
import { LoginView } from "./components/LoginView";
import { EventsView } from "./components/EventsView";
import { UsersView } from "./components/UsersView";

type Tab = "events" | "users";

const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super Admin",
  tenant_admin: "Tenant Admin",
  user: "Attendee",
};

function Shell({ fetchImpl }: { fetchImpl: typeof fetch }) {
  const { user, token, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("events");

  // Every data call carries the bearer token.
  const authedFetch = useMemo(
    () => makeAuthedFetch(token, fetchImpl),
    [token, fetchImpl],
  );

  if (!user) return null; // guarded by the caller
  const isAdmin = user.role === "super_admin" || user.role === "tenant_admin";

  return (
    <div className="atelier-shell">
      <AppBar themeColor="dark">
        <AppBarSection>
          <strong>Convergence Atelier</strong>
        </AppBarSection>
        <AppBarSpacer />
        <AppBarSection className="atelier-nav">
          <Button
            fillMode={tab === "events" ? "solid" : "flat"}
            onClick={() => setTab("events")}
            data-testid="nav-events"
          >
            Events
          </Button>
          {isAdmin && (
            <Button
              fillMode={tab === "users" ? "solid" : "flat"}
              onClick={() => setTab("users")}
              data-testid="nav-users"
            >
              Users
            </Button>
          )}
        </AppBarSection>
        <AppBarSpacer />
        <AppBarSection>
          <span className="atelier-whoami" data-testid="whoami">
            {user.email} · {ROLE_LABEL[user.role] ?? user.role}
          </span>
          <Button fillMode="flat" onClick={logout} data-testid="logout">
            Sign out
          </Button>
        </AppBarSection>
      </AppBar>

      <main className="atelier-main">
        {tab === "events" && (
          <EventsView fetchImpl={authedFetch} canWrite={user.role !== "user"} />
        )}
        {tab === "users" && isAdmin && <UsersView fetchImpl={authedFetch} />}
      </main>
    </div>
  );
}

function Gate({ fetchImpl }: { fetchImpl: typeof fetch }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="atelier-loading" data-testid="auth-loading">
        <Loader type="infinite-spinner" />
      </div>
    );
  }
  if (!user) return <LoginView fetchImpl={fetchImpl} />;
  return <Shell fetchImpl={fetchImpl} />;
}

interface AppProps {
  fetchImpl?: typeof fetch;
  store?: TokenStore;
}

export function App({ fetchImpl = fetch, store }: AppProps) {
  return (
    <AuthProvider fetchImpl={fetchImpl} store={store}>
      <Gate fetchImpl={fetchImpl} />
    </AuthProvider>
  );
}

export default App;
