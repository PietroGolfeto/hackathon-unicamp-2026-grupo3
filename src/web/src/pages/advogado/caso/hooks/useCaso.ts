import { notifications } from "@mantine/notifications";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useParams } from "react-router";

import { api, type DecisaoRegistrada } from "../../../../api/client";
import type { DocumentosAbertos } from "../caso.types";

/** Processo, recomendação e o estado da sessão de análise (documentos abertos, cronômetro, decisão). */
export function useCaso() {
  const { id } = useParams();
  const pid = Number(id);
  const qc = useQueryClient();
  const processo = useQuery({ queryKey: ["processo", pid], queryFn: () => api.processo(pid), enabled: !!pid });
  const recomendacao = useQuery({ queryKey: ["recomendacao", pid], queryFn: () => api.recomendacao(pid), enabled: !!pid });
  const [registrada, setRegistrada] = useState<DecisaoRegistrada | null>(null);
  const [novaDecisao, setNovaDecisao] = useState(false);
  const [abertos, setAbertos] = useState<DocumentosAbertos>(new Set());
  const inicio = useRef(Date.now());

  const invalidar = () => {
    qc.invalidateQueries({ queryKey: ["processo", pid] });
    qc.invalidateQueries({ queryKey: ["processos"] });
  };

  const abrirDocumento = (arquivo: string) => setAbertos((s) => new Set(s).add(arquivo));

  const aoRegistrarDecisao = (r: DecisaoRegistrada) => {
    setRegistrada(r);
    setNovaDecisao(false);
    invalidar();
    notifications.show({ title: "Decisão registrada", message: r.mensagem, color: r.decisao.aderente ? "verde" : "laranja" });
  };

  const p = processo.data;
  const decisaoAtual = registrada?.decisao ?? p?.decisao_atual ?? null;

  return {
    pid, processo, recomendacao, p, registrada, decisaoAtual,
    mostrarForm: !decisaoAtual || novaDecisao,
    mostrarDecisaoAtual: !!decisaoAtual && !novaDecisao,
    abertos, abrirDocumento,
    inicio: inicio.current,
    aoRegistrarDecisao,
    pedirNovaDecisao: () => setNovaDecisao(true),
    invalidar,
  };
}
