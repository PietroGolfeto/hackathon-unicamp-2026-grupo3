import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { createElement, useEffect } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";

import { api, type Papel, type Usuario } from "../api/client";

const SENHA_DEMO = "senha123";
const CONTA_DEMO: Record<Papel, string> = {
  advogado: "adv1@escritorio-a",
  gestor: "gestor@banco-ufmg",
};

export function homeDe(u: Usuario): string {
  return u.papel === "gestor" ? "/gestor/painel" : "/casos";
}

export function useSession() {
  return useQuery({ queryKey: ["me"], queryFn: api.me, retry: false, staleTime: 5 * 60_000 });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.logout,
    onSettled: () => {
      qc.clear();
      window.location.assign("/");
    },
  });
}

/** Troca instantaneamente entre a conta de demonstração do advogado e a do gestor, sem passar por tela de login. */
export function useTrocarPapel() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (papel: Papel) => api.login(CONTA_DEMO[papel], SENHA_DEMO),
    onSuccess: (u) => {
      qc.setQueryData(["me"], u);
      navigate(homeDe(u), { replace: true });
    },
  });
}

/**
 * Sem tela de login: se não há sessão, entra sozinho com a conta de demonstração certa para a área visitada
 * (gestor em `/gestor/*`, advogado no resto), para que um link direto caia na tela pedida.
 */
export function RequireAuth({ papel, children }: { papel?: Papel; children: ReactNode }) {
  const { data, isLoading } = useSession();
  const location = useLocation();
  const qc = useQueryClient();
  const papelPadrao: Papel = papel ?? (location.pathname.startsWith("/gestor") ? "gestor" : "advogado");
  const entrar = useMutation({
    mutationFn: () => api.login(CONTA_DEMO[papelPadrao], SENHA_DEMO),
    onSuccess: (u) => qc.setQueryData(["me"], u),
  });

  useEffect(() => {
    if (!isLoading && !data && entrar.isIdle) entrar.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, data]);

  if (entrar.isError) {
    return createElement(
      "div",
      { style: { padding: 24, fontFamily: "sans-serif" } },
      createElement("p", null, "Não foi possível entrar automaticamente."),
      createElement("button", { onClick: () => entrar.mutate() }, "Tentar de novo"),
    );
  }
  if (isLoading || !data) return null;
  if (papel && data.papel !== papel) return createElement(Navigate, { to: homeDe(data), replace: true });
  return children;
}
