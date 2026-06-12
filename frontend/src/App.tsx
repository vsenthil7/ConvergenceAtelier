import { useEffect, useState } from "react";
import { AppBar, AppBarSection, AppBarSpacer } from "@progress/kendo-react-layout";
import { getHealth, type HealthStatus } from "./lib/api";
import { EventsView } from "./components/EventsView";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; data: HealthStatus }
  | { kind: "error"; message: string };

export function App({ fetchImpl = fetch }: { fetchImpl?: typeof fetch }) {
  const [state, setState] = useState<State>({ kind: "idle" });

  const check = async () => {
    setState({ kind: "loading" });
    try {
      const data = await getHealth(fetchImpl);
      setState({ kind: "ok", data });
    } catch (e) {
      setState({ kind: "error", message: e instanceof Error ? e.message : "Unknown error" });
    }
  };

  useEffect(() => {
    void check();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="atelier-shell">
      <AppBar themeColor="dark">
        <AppBarSection>
          <strong>Convergence Atelier</strong>
        </AppBarSection>
        <AppBarSpacer />
        <AppBarSection>
          {state.kind === "ok" && (
            <span className="atelier-tagline" data-testid="health-ok">
              {state.data.service} · {state.data.mode}
            </span>
          )}
          {state.kind === "error" && (
            <span className="atelier-tagline" role="alert" data-testid="health-error">
              backend offline
            </span>
          )}
        </AppBarSection>
      </AppBar>

      <main className="atelier-main">
        <EventsView fetchImpl={fetchImpl} />
      </main>
    </div>
  );
}

export default App;
