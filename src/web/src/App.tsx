import { Navigate, Outlet, Route, Routes } from "react-router";

import { RequireAuth, homeDe, useSession } from "./auth/useSession";
import { Layout } from "./components/Layout";
import Login from "./pages/Login";
import Caso from "./pages/advogado/Caso";
import Casos from "./pages/advogado/Casos";
import Aprovacoes from "./pages/gestor/Aprovacoes";
import Painel from "./pages/gestor/Painel";
import Politica from "./pages/gestor/Politica";

function Inicio() {
  const { data, isLoading } = useSession();
  if (isLoading) return null;
  return <Navigate to={data ? homeDe(data) : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route path="/casos" element={<Casos />} />
        <Route path="/casos/:id" element={<Caso />} />
        <Route element={<RequireAuth papel="gestor"><Outlet /></RequireAuth>}>
          <Route path="/gestor/painel" element={<Painel />} />
          <Route path="/gestor/politica" element={<Politica />} />
          <Route path="/gestor/aprovacoes" element={<Aprovacoes />} />
        </Route>
      </Route>
      <Route path="*" element={<Inicio />} />
    </Routes>
  );
}
