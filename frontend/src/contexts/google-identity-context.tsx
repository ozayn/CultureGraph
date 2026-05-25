"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/contexts/auth-context";
import {
  initializeGoogleIdentityOnce,
  loadGoogleIdentityScript,
  setGoogleCredentialHandler,
} from "@/lib/google-identity";

interface GoogleIdentityContextValue {
  ready: boolean;
  error: string | null;
}

const GoogleIdentityContext = createContext<GoogleIdentityContextValue | null>(null);

interface GoogleIdentityProviderProps {
  clientId: string;
  children: ReactNode;
}

export function GoogleIdentityProvider({ clientId, children }: GoogleIdentityProviderProps) {
  const { signInWithGoogleToken } = useAuth();
  const signInRef = useRef(signInWithGoogleToken);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    signInRef.current = signInWithGoogleToken;
  });

  useEffect(() => {
    let cancelled = false;

    setGoogleCredentialHandler((credential) => {
      void signInRef.current(credential).catch(() => {
        // AuthProvider stores the user-visible sign-in error.
      });
    });

    void (async () => {
      try {
        await loadGoogleIdentityScript();
        if (cancelled) return;

        initializeGoogleIdentityOnce(clientId);
        if (cancelled) return;

        setReady(true);
        setError(null);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Could not initialize Google sign-in.");
        }
      }
    })();

    return () => {
      cancelled = true;
      setGoogleCredentialHandler(null);
    };
  }, [clientId]);

  return (
    <GoogleIdentityContext.Provider value={{ ready, error }}>
      {children}
    </GoogleIdentityContext.Provider>
  );
}

export function useGoogleIdentity(): GoogleIdentityContextValue {
  const context = useContext(GoogleIdentityContext);
  if (!context) {
    throw new Error("useGoogleIdentity must be used within GoogleIdentityProvider.");
  }
  return context;
}
