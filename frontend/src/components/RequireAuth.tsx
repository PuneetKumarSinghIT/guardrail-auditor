import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { isAuthenticated } from "../lib/auth";

// Route guard — checks for an active Cognito session before rendering children.
// Unauthenticated users are redirected to /login.
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<"checking" | "in" | "out">("checking");

  useEffect(() => {
    let active = true;
    isAuthenticated().then((ok) => {
      if (active) setState(ok ? "in" : "out");
    });
    return () => {
      active = false;
    };
  }, []);

  if (state === "checking") {
    return (
      <div className="flex min-h-full items-center justify-center text-sm text-slate-400">
        Loading…
      </div>
    );
  }
  if (state === "out") {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
