import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Layout from "./components/Layout";
import Overview from "./pages/Overview";
import GrowthRevenue from "./pages/GrowthRevenue";
import Profitability from "./pages/Profitability";
import CashLiquidity from "./pages/CashLiquidity";
import SolvencyLeverage from "./pages/SolvencyLeverage";
import Returns from "./pages/Returns";
import UploadReport from "./pages/UploadReport";

const SESSION_KEY = "senus_board_session";

function safeGet(key) {
  try { return window.localStorage.getItem(key); } catch { return null; }
}
function safeSet(key, val) {
  try { window.localStorage.setItem(key, val); } catch { /* no-op */ }
}
function safeRemove(key) {
  try { window.localStorage.removeItem(key); } catch { /* no-op */ }
}

function useSession() {
  const [user, setUser] = useState(() => {
    const raw = safeGet(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  });

  useEffect(() => {
    if (user) safeSet(SESSION_KEY, JSON.stringify(user));
    else safeRemove(SESSION_KEY);
  }, [user]);

  return { user, setUser };
}

export default function App() {
  const { user, setUser } = useSession();

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/" replace /> : <Login onLogin={setUser} />}
        />
        <Route
          path="/*"
          element={
            user ? (
              <Layout user={user} onLogout={() => setUser(null)}>
                <Routes>
                  <Route path="/" element={<Overview />} />
                  <Route path="/growth" element={<GrowthRevenue />} />
                  <Route path="/profitability" element={<Profitability />} />
                  <Route path="/cash" element={<CashLiquidity />} />
                  <Route path="/solvency" element={<SolvencyLeverage />} />
                  <Route path="/returns" element={<Returns />} />
                  <Route path="/upload" element={<UploadReport />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Layout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}