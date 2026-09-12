import { useReducedMotion } from "@mantine/hooks";
import { useEffect, useRef, useState } from "react";

/**
 * Leva um número do valor mostrado até `alvo` em `ms`, com ease-out. Começa em zero no primeiro render
 * e, quando o alvo muda (poll do painel, simulação da política), anda do valor atual ao novo.
 * Com prefers-reduced-motion, salta direto.
 */
export function useContagem(alvo: number | null | undefined, ms = 700): number {
  const reduzido = useReducedMotion();
  const [atual, setAtual] = useState(0);
  const mostrado = useRef(0);

  useEffect(() => {
    if (alvo == null || !Number.isFinite(alvo)) return;
    if (reduzido) {
      mostrado.current = alvo;
      setAtual(alvo);
      return;
    }
    const de = mostrado.current;
    const inicio = performance.now();
    let frame = 0;
    const passo = (t: number) => {
      const p = Math.min(1, (t - inicio) / ms);
      const suave = 1 - Math.pow(1 - p, 3);
      mostrado.current = de + (alvo - de) * suave;
      setAtual(mostrado.current);
      if (p < 1) frame = requestAnimationFrame(passo);
    };
    frame = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(frame);
  }, [alvo, ms, reduzido]);

  return alvo == null ? 0 : atual;
}

/** Vira `true` um quadro depois de montar: barras que começam em zero e crescem até o valor. */
export function useMontado(): boolean {
  const [pronto, setPronto] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setPronto(true));
    return () => cancelAnimationFrame(id);
  }, []);
  return pronto;
}
