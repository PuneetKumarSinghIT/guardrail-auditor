import { useNavigate } from "react-router-dom";
import { signOut } from "../lib/auth";

// Shared top bar with brand + sign-out. Used by both list and detail pages.
export function AppHeader() {
  const navigate = useNavigate();

  const onSignOut = async () => {
    await signOut();
    navigate("/login");
  };

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <button
          onClick={() => navigate("/scans")}
          className="text-lg font-bold text-slate-900 hover:text-blue-700"
        >
          🛡️ Security Guardrail Auditor
        </button>
        <button
          onClick={onSignOut}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
