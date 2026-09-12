import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api } from "../../../../api/client";
import { useSession } from "../../../../auth/useSession";
import { COLUNAS_BASE } from "../casos.const";
import type { Situacao } from "../casos.types";

/** Lista de processos com filtro de situação e busca por número ou autor. */
export function useCasos() {
  const [busca, setBusca] = useState("");
  const [situacao, setSituacao] = useState<Situacao>("todos");
  const { data: usuario } = useSession();
  const { data, isLoading, error } = useQuery({ queryKey: ["processos"], queryFn: () => api.processos() });
  const gestor = usuario?.papel === "gestor";

  const filtrados = useMemo(() => {
    const termo = busca.replace(/\D/g, "");
    const texto = busca.trim().toLowerCase();
    return (data ?? []).filter((p) => {
      if (situacao === "pendente" && p.status !== "pendente") return false;
      if (situacao === "decidido" && p.status === "pendente") return false;
      if (!texto) return true;
      return (termo !== "" && p.numero.replace(/\D/g, "").includes(termo)) || (p.autor ?? "").toLowerCase().includes(texto);
    });
  }, [data, busca, situacao]);

  const pendentes = (data ?? []).filter((p) => p.status === "pendente").length;
  const temAutor = (data ?? []).some((p) => p.autor); // só com P3 plugado
  const colunas = COLUNAS_BASE + (temAutor ? 1 : 0) + (gestor ? 1 : 0);

  return {
    busca, setBusca, situacao, setSituacao,
    usuario, gestor, processos: data, filtrados,
    pendentes, temAutor, colunas,
    isLoading, error: error as Error | null,
  };
}
