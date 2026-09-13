import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { api } from "../../../../api/client";

/**
 * Dispara a inferência dos casos ao abrir a tela e acompanha o progresso.
 *
 * A primeira execução é o POST que dispara; as seguintes são o GET do poll. Depois de `pronto`
 * nada mais roda: `staleTime: Infinity` guarda o estado por toda a sessão, e do lado do servidor
 * o cache do extractor e o banco evitam qualquer chamada nova de LLM.
 */
export function usePreparacao() {
  const qc = useQueryClient();
  const disparado = useRef(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["preparacao"],
    queryFn: () => {
      if (disparado.current) return api.preparacao();
      disparado.current = true;
      return api.prepararCasos();
    },
    refetchInterval: (q) => (q.state.data?.status === "rodando" ? 1500 : false),
    staleTime: Infinity,
    gcTime: Infinity,
  });

  const pronto = data?.status === "pronto" || data?.status === "erro";

  useEffect(() => {
    if (pronto) qc.invalidateQueries({ queryKey: ["processos"] });
  }, [pronto, qc]);

  return {
    preparacao: data,
    pronto,
    preparando: isLoading || data?.status === "rodando",
    erroPreparacao: (error as Error | null)?.message ?? data?.erro ?? null,
  };
}
