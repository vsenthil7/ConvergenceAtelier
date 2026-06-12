import { useCallback, useEffect, useState } from "react";
import { Grid, GridColumn } from "@progress/kendo-react-grid";
import { Input } from "@progress/kendo-react-inputs";
import { DropDownList } from "@progress/kendo-react-dropdowns";
import { Button } from "@progress/kendo-react-buttons";
import { Loader } from "@progress/kendo-react-indicators";
import {
  createManagedUser,
  listUsers,
  type ManagedUser,
  type Role,
} from "../lib/auth";
import { useAuth } from "../lib/AuthContext";

interface Props {
  fetchImpl?: typeof fetch;
}

// Roles a tenant-admin may assign (no super_admin); super-admins may assign all.
const ROLE_OPTIONS: { super: Role[]; tenant: Role[] } = {
  super: ["user", "tenant_admin", "super_admin"],
  tenant: ["user", "tenant_admin"],
};

export function UsersView({ fetchImpl = fetch }: Props) {
  const { user, token } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("user");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const roleChoices =
    user?.role === "super_admin" ? ROLE_OPTIONS.super : ROLE_OPTIONS.tenant;

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      setUsers(await listUsers(token, fetchImpl));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, [token, fetchImpl]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const addUser = async () => {
    if (!token) return;
    setSaving(true);
    setFormError(null);
    try {
      await createManagedUser(
        token,
        { email, full_name: fullName, password, role },
        fetchImpl,
      );
      setEmail("");
      setFullName("");
      setPassword("");
      setRole("user");
      await refresh();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  const canSubmit = email.length > 0 && password.length >= 8;

  return (
    <section className="users-view">
      <h2>Users</h2>
      {loading && <Loader type="infinite-spinner" />}
      {error && (
        <p role="alert" data-testid="users-error">
          {error}
        </p>
      )}

      {!loading && !error && (
        <div data-testid="users-grid">
          <Grid data={users} scrollable="none">
            <GridColumn field="email" title="Email" />
            <GridColumn field="full_name" title="Name" />
            <GridColumn field="role" title="Role" />
            <GridColumn field="auth_provider" title="Provider" />
          </Grid>
        </div>
      )}

      <div className="users-add" data-testid="users-add">
        <h3>Add a user</h3>
        <label>
          Email
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(String(e.value ?? ""))}
            aria-label="new-user-email"
          />
        </label>
        <label>
          Full name
          <Input
            value={fullName}
            onChange={(e) => setFullName(String(e.value ?? ""))}
            aria-label="new-user-name"
          />
        </label>
        <label>
          Password
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(String(e.value ?? ""))}
            aria-label="new-user-password"
          />
        </label>
        <label>
          Role
          <DropDownList
            data={roleChoices}
            value={role}
            onChange={(e) => setRole(e.value as Role)}
            aria-label="new-user-role"
          />
        </label>
        {formError && (
          <p role="alert" data-testid="users-form-error">
            {formError}
          </p>
        )}
        <Button
          themeColor="primary"
          onClick={() => void addUser()}
          disabled={saving || !canSubmit}
          data-testid="users-add-submit"
        >
          Add user
        </Button>
      </div>
    </section>
  );
}
