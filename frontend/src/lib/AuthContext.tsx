import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  getMe,
  login as apiLogin,
  loginGoogle as apiLoginGoogle,
  type CurrentUser,
} from "./auth";

const TOKEN_KEY = "atelier.token";

export interface TokenStore {
  get(): string | null;
  set(token: string): void;
  clear(): void;
}

/** Default store backed by localStorage; falls back to memory if unavailable. */
export function browserTokenStore(): TokenStore {
  let memory: string | null = null;
  const hasLS = (() => {
    try {
      return typeof window !== "undefined" && !!window.localStorage;
    } catch {
      return false;
    }
  })();
  return {
    get() {
      if (hasLS) return window.localStorage.getItem(TOKEN_KEY);
      return memory;
    },
    set(token: string) {
      if (hasLS) window.localStorage.setItem(TOKEN_KEY, token);
      else memory = token;
    },
    clear() {
      if (hasLS) window.localStorage.removeItem(TOKEN_KEY);
      else memory = null;
    },
  };
}

export interface AuthState {
  user: CurrentUser | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

interface ProviderProps {
  children: ReactNode;
  fetchImpl?: typeof fetch;
  store?: TokenStore;
}

export function AuthProvider({ children, fetchImpl = fetch, store }: ProviderProps) {
  const tokenStore = useMemo(() => store ?? browserTokenStore(), [store]);
  const [token, setToken] = useState<string | null>(() => tokenStore.get());
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // On mount (or token change) resolve the current user.
  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    getMe(token, fetchImpl)
      .then((u) => {
        if (!cancelled) {
          setUser(u);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          // Token invalid/expired — clear it.
          tokenStore.clear();
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, fetchImpl, tokenStore]);

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      try {
        const { access_token } = await apiLogin(email, password, fetchImpl);
        tokenStore.set(access_token);
        setToken(access_token);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Login failed");
        throw e;
      }
    },
    [fetchImpl, tokenStore],
  );

  const loginWithGoogle = useCallback(
    async (idToken: string) => {
      setError(null);
      try {
        const { access_token } = await apiLoginGoogle(idToken, fetchImpl);
        tokenStore.set(access_token);
        setToken(access_token);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Google login failed");
        throw e;
      }
    },
    [fetchImpl, tokenStore],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setToken(null);
    setUser(null);
  }, [tokenStore]);

  const value = useMemo<AuthState>(
    () => ({ user, token, loading, error, login, loginWithGoogle, logout }),
    [user, token, loading, error, login, loginWithGoogle, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
