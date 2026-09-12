import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { createElement } from "react";
import { Navigate, useLocation } from "react-router";

import { api, type Papel, type Usuario } from "../api/client";

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
      window.location.assign("/login");
    },
  });
}

export function RequireAuth({ papel, children }: { papel?: Papel; children: ReactNode }) {
  const { data, isLoading } = useSession();
  const location = useLocation();
  if (isLoading) return null;
  if (!data) return createElement(Navigate, { to: "/login", replace: true, state: { de: location.pathname } });
  if (papel && data.papel !== papel) return createElement(Navigate, { to: homeDe(data), replace: true });
  return children;
}
