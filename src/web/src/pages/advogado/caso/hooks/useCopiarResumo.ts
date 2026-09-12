import { notifications } from "@mantine/notifications";
import { useMutation } from "@tanstack/react-query";

import { api } from "../../../../api/client";

/** Copia o resumo do processo para a área de transferência (WhatsApp, e-mail). */
export function useCopiarResumo(pid: number) {
  return useMutation({
    mutationFn: () => api.resumoTxt(pid).then((t) => navigator.clipboard.writeText(t)),
    onSuccess: () => notifications.show({ message: "Resumo copiado. Cole no WhatsApp ou no e-mail.", color: "verde" }),
    onError: (e) => notifications.show({ message: (e as Error).message, color: "vermelho" }),
  });
}
