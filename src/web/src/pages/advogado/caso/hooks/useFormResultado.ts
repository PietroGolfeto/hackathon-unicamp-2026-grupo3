import { notifications } from "@mantine/notifications";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api, type Decisao, type Resultado } from "../../../../api/client";
import { ROTULO_RESULTADO } from "../../../../lib/format";

/** Resultado da negociação. Defesa só tem um desfecho possível; acordo tem quatro. */
export function useFormResultado({ d, onOk }: { d: Decisao; onOk: () => void }) {
  const opcoes = useMemo(() => d.tipo === "defesa"
    ? [{ value: "seguiu_defesa", label: ROTULO_RESULTADO.seguiu_defesa }]
    : ["aceito", "contraproposta_aceita", "recusado", "sem_resposta"].map((v) => ({ value: v, label: ROTULO_RESULTADO[v] })), [d.tipo]);
  const [resultado, setResultado] = useState<Resultado | null>(d.tipo === "defesa" ? "seguiu_defesa" : null);
  const [valorFinal, setValorFinal] = useState<number | null>(d.valor_proposto);
  const [obs, setObs] = useState("");
  const precisaValor = resultado === "aceito" || resultado === "contraproposta_aceita";

  const registrar = useMutation({
    mutationFn: () => api.resultado(d.id, { resultado: resultado!, valor_final: precisaValor ? valorFinal : null, observacao: obs || null }),
    onSuccess: () => { notifications.show({ message: "Resultado registrado.", color: "verde" }); onOk(); },
  });

  return { opcoes, resultado, setResultado, valorFinal, setValorFinal, obs, setObs, precisaValor, registrar };
}
