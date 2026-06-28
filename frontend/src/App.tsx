import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./pages/LoginPage";
import { ScanListPage } from "./pages/ScanListPage";
import { ScanDetailPage } from "./pages/ScanDetailPage";
import { RequireAuth } from "./components/RequireAuth";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/scans"
        element={
          <RequireAuth>
            <ScanListPage />
          </RequireAuth>
        }
      />
      <Route
        path="/scans/:id"
        element={
          <RequireAuth>
            <ScanDetailPage />
          </RequireAuth>
        }
      />
      <Route path="/" element={<Navigate to="/scans" replace />} />
      <Route path="*" element={<Navigate to="/scans" replace />} />
    </Routes>
  );
}
