import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api, type DecisaoRegistrada, type Recomendacao, type TipoDecisao } from "../../../../api/client";
import type { DocumentosAbertos } from "../caso.types";

/** Formulário de decisão: tipo, valor, justificativa e o cronômetro do tempo de análise. */
export function useFormDecisao({ pid, rec, abertos, inicio, onOk }: {
  pid: number; rec: Recomendacao; abertos: DocumentosAbertos; inicio: number; onOk: (r: DecisaoRegistrada) => void;
}) {
  // O advogado decide acordo ou defesa. "instruir" é um acordo adiado: a aderência é medida
  // contra ele, então é ele que vem pré-selecionado. Mesma regra do backend.
  const esperado: TipoDecisao = rec.tipo === "instruir" ? "acordo" : rec.tipo;
  const [tipo, setTipo] = useState<TipoDecisao>(esperado);
  const [valor, setValor] = useState<number | null>(rec.valor_sugerido);
  const [justificativa, setJustificativa] = useState("");
  const [segundos, setSegundos] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setSegundos(Math.floor((Date.now() - inicio) / 1000)), 1000);
    return () => clearInterval(t);
  }, [inicio]);

  const foraDaBanda = tipo === "acordo" && valor != null &&
    rec.valor_min != null && rec.valor_max != null && (valor < rec.valor_min || valor > rec.valor_max);
  const diverge = tipo !== esperado || foraDaBanda;

  const registrar = useMutation({
    mutationFn: () => api.decidir(pid, {
      tipo, valor_proposto: tipo === "acordo" ? valor : null, justificativa: justificativa || null,
      tempo_analise_s: Math.floor((Date.now() - inicio) / 1000), documentos_abertos: [...abertos],
    }),
    onSuccess: onOk,
  });

  return { tipo, setTipo, valor, setValor, justificativa, setJustificativa, segundos, foraDaBanda, diverge, registrar };
}
