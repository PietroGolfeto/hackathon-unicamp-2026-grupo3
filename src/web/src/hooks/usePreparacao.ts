import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { api } from "../api/client";

/** Só a primeira chamada da sessão dispara a preparação; as seguintes são o poll. */
let disparado = false;

/**
 * Dispara a preparação dos casos e acompanha o que ainda roda no servidor.
 *
 * O POST volta assim que a fase 1 termina — processos, documentos, subsídios e scores, em
 * milissegundos —, então a lista e o caso já podem carregar. A fase 2 (leitura dos PDFs pelo LLM)
 * segue em background e chega por poll de 1,5 s (decisão 14, nunca websocket). A cada caso que
 * fica pronto, as queries de processo são invalidadas: quem estiver com a tela aberta vê o resumo
 * e a recomendação aparecerem sozinhos, sem recarregar nada.
 */
export function usePreparacao() {
  const qc = useQueryClient();
  const { data, isSuccess, error } = useQuery({
    queryKey: ["preparacao"],
    queryFn: async () => {
      if (disparado) return api.preparacao();
      const estado = await api.prepararCasos();
      disparado = true;
      return estado;
    },
    refetchInterval: (q) => (q.state.data?.status === "rodando" ? 1500 : false),
    staleTime: Infinity,
    gcTime: Infinity,
  });

  // "3 de 5 prontos" virou "4 de 5": algum caso acabou de ganhar resumo e recomendação.
  const marco = data ? `${data.status}:${data.prontos}` : null;
  const anterior = useRef<string | null>(null);
  useEffect(() => {
    if (marco === null) return;
    if (anterior.current !== null && anterior.current !== marco) {
      qc.invalidateQueries({ queryKey: ["processos"] });
      qc.invalidateQueries({ queryKey: ["processo"] });
    }
    anterior.current = marco;
  }, [marco, qc]);

  return {
    preparacao: data,
    /** Fase 1 respondida: os processos existem e a tela pode carregar. */
    base: isSuccess,
    /** Fase 2 em andamento: alguns casos ainda não foram lidos. */
    lendoDocumentos: data?.status === "rodando",
    erroPreparacao: (error as Error | null)?.message ?? data?.erro ?? null,
  };
}
