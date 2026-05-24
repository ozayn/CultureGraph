const GSI_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

type CredentialCallback = (credential: string) => void;

let scriptLoadPromise: Promise<void> | null = null;
let initializedClientId: string | null = null;
let credentialCallback: CredentialCallback | null = null;

export function setGoogleCredentialHandler(handler: CredentialCallback | null): void {
  credentialCallback = handler;
}

export function isGoogleIdentityInitialized(clientId: string): boolean {
  return initializedClientId === clientId;
}

export function loadGoogleIdentityScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.resolve();
  }

  if (window.google?.accounts?.id) {
    return Promise.resolve();
  }

  if (scriptLoadPromise) {
    return scriptLoadPromise;
  }

  scriptLoadPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${GSI_SCRIPT_SRC}"]`
    );

    if (existing) {
      if (window.google?.accounts?.id) {
        resolve();
        return;
      }
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener(
        "error",
        () => reject(new Error("Failed to load Google Identity Services.")),
        { once: true }
      );
      return;
    }

    const script = document.createElement("script");
    script.src = GSI_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Identity Services."));
    document.head.appendChild(script);
  });

  return scriptLoadPromise;
}

export function initializeGoogleIdentityOnce(clientId: string): void {
  if (typeof window === "undefined" || !window.google?.accounts?.id) {
    throw new Error("Google Identity Services is not available.");
  }

  if (initializedClientId === clientId) {
    return;
  }

  if (initializedClientId) {
    console.warn(
      "Google Identity Services already initialized for a different client id."
    );
    return;
  }

  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: (response: { credential?: string }) => {
      if (response.credential && credentialCallback) {
        credentialCallback(response.credential);
      }
    },
  });

  initializedClientId = clientId;
}

export function resetGoogleIdentityForTests(): void {
  initializedClientId = null;
  scriptLoadPromise = null;
  credentialCallback = null;
}

export function renderGoogleSignInButton(
  parent: HTMLElement,
  options?: {
    theme?: "outline" | "filled_blue" | "filled_black";
    size?: "large" | "medium" | "small";
    text?: "signin_with" | "continue_with" | "signin";
    shape?: "rectangular" | "pill" | "circle" | "square";
    width?: number;
  }
): void {
  if (!window.google?.accounts?.id) {
    throw new Error("Google Identity Services is not available.");
  }

  parent.replaceChildren();

  window.google.accounts.id.renderButton(parent, {
    type: "standard",
    theme: options?.theme ?? "outline",
    size: options?.size ?? "large",
    text: options?.text ?? "signin_with",
    shape: options?.shape ?? "rectangular",
    width: options?.width ?? 280,
  });
}
