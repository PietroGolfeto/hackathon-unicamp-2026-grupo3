import type { SVGProps } from "react";

/** Ícones em SVG inline (traço 1.8, 24×24) para não adicionar dependência. Cor = currentColor. */
type Props = SVGProps<SVGSVGElement> & { size?: number };

function Ico({ size = 16, children, ...rest }: Props) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" style={{ flex: "none" }} {...rest}>
      {children}
    </svg>
  );
}

export const IcoEnter = (p: Props) => <Ico {...p}><path d="M20 5v8H7" /><path d="m10 9-4 4 4 4" /></Ico>;
export const IcoBusca = (p: Props) => <Ico {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Ico>;
export const IcoVoltar = (p: Props) => <Ico {...p}><path d="M19 12H5" /><path d="m12 19-7-7 7-7" /></Ico>;
export const IcoSeta = (p: Props) => <Ico {...p}><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></Ico>;
export const IcoBaixo = (p: Props) => <Ico {...p}><path d="m6 9 6 6 6-6" /></Ico>;
export const IcoCopiar = (p: Props) => <Ico {...p}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h9" /></Ico>;
export const IcoDoc = (p: Props) => <Ico {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /></Ico>;
export const IcoCheck = (p: Props) => <Ico {...p}><path d="m5 12 5 5L20 7" /></Ico>;
export const IcoX = (p: Props) => <Ico {...p}><path d="M6 6l12 12" /><path d="M18 6 6 18" /></Ico>;
export const IcoAlerta = (p: Props) => (
  <Ico {...p}><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 3.9 2.6 17.2A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0z" /></Ico>
);
export const IcoRelogio = (p: Props) => <Ico {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Ico>;
export const IcoSair = (p: Props) => <Ico {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="m16 17 5-5-5-5" /><path d="M21 12H9" /></Ico>;
export const IcoExterno = (p: Props) => (
  <Ico {...p}><path d="M14 4h6v6" /><path d="M20 4 10 14" /><path d="M20 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h5" /></Ico>
);
export const IcoEscudo = (p: Props) => <Ico {...p}><path d="M12 3 4 6v6c0 5 3.4 8.4 8 9 4.6-.6 8-4 8-9V6z" /></Ico>;
export const IcoAcordo = (p: Props) => <Ico {...p}><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-6" /></Ico>;
export const IcoPessoa = (p: Props) => <Ico {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></Ico>;
export const IcoRaio = (p: Props) => <Ico {...p}><path d="M13 2 4 14h7l-1 8 9-12h-7z" /></Ico>;
