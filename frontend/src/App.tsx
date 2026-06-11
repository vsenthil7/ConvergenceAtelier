import { useEffect, useState } from "react";
import { AppBar, AppBarSection, AppBarSpacer, Card, CardBody, CardTitle } from "@progress/kendo-react-layout";
import { Button } from "@progress/kendo-react-buttons";
import { Loader } from "@progress/kendo-react-indicators";
import { getHealth, type HealthStatus } from "./lib/api";

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
          <span className="atelier-tagline">Conference organiser studio</span>
        </AppBarSection>
      </AppBar>

      <main className="atelier-main">
        <Card>
          <CardBody>
            <CardTitle>System status</CardTitle>
            {state.kind === "loading" && <Loader type="infinite-spinner" />}
            {state.kind === "ok" && (
              <ul data-testid="health-ok">
                <li>Status: {state.data.status}</li>
                <li>Service: {state.data.service}</li>
                <li>Mode: {state.data.mode}</li>
                <li>Version: {state.data.version}</li>
              </ul>
            )}
            {state.kind === "error" && (
              <p data-testid="health-error" role="alert">
                Couldn&apos;t reach the backend: {state.message}
              </p>
            )}
            <Button themeColor="primary" onClick={() => void check()}>
              Refresh status
            </Button>
          </CardBody>
        </Card>
      </main>
    </div>
  );
}

export default App;
