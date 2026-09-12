import { Center, Loader } from "@mantine/core";
import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router";

import { RequireAuth, homeDe, useSession } from "./auth/useSession";
import { Layout } from "./components/Layout";

const Caso = lazy(() => import("./pages/advogado/Caso"));
const Casos = lazy(() => import("./pages/advogado/Casos"));
const Aprovacoes = lazy(() => import("./pages/gestor/Aprovacoes"));
const Painel = lazy(() => import("./pages/gestor/Painel"));
const Politica = lazy(() => import("./pages/gestor/Politica"));

function Carregando() {
  return <Center h={320}><Loader color="laranja" /></Center>;
}

function Inicio() {
  const { data, isLoading } = useSession();
  if (isLoading) return null;
  return <Navigate to={data ? homeDe(data) : "/casos"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route path="/casos" element={<Suspense fallback={<Carregando />}><Casos /></Suspense>} />
        <Route path="/casos/:id" element={<Suspense fallback={<Carregando />}><Caso /></Suspense>} />
        <Route element={<RequireAuth papel="gestor"><Outlet /></RequireAuth>}>
          <Route path="/gestor/painel" element={
            <Suspense fallback={<Carregando />}><Painel /></Suspense>
          } />
          <Route path="/gestor/politica" element={<Suspense fallback={<Carregando />}><Politica /></Suspense>} />
          <Route path="/gestor/aprovacoes" element={<Suspense fallback={<Carregando />}><Aprovacoes /></Suspense>} />
        </Route>
      </Route>
      <Route path="*" element={<Inicio />} />
    </Routes>
  );
}
