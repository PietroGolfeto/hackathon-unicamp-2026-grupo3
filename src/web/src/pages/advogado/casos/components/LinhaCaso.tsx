import { Anchor, Group, Loader, Table, Text, Tooltip } from "@mantine/core";
import { Link } from "react-router";

import type { ProcessoResumo } from "../../../../api/client";
import { StatusBadge, TipoBadge } from "../../../../components/Badges";
import { brl } from "../../../../lib/format";
import { SubsidiosTracos } from "./SubsidiosTracos";

export function LinhaCaso({ p, gestor, temAutor, onSelecionar }: {
  p: ProcessoResumo; gestor: boolean; temAutor: boolean; onSelecionar: (id: number) => void;
}) {
  return (
    <Table.Tr className="linha-link" onClick={() => onSelecionar(p.id)}>
      <Table.Td>
        <Anchor component={Link} to={`/casos/${p.id}`} fw={500} size="sm" c="tinta.6" className="numero"
          onClick={(e) => e.stopPropagation()}>
          {p.numero}
        </Anchor>
      </Table.Td>
      {temAutor && <Table.Td><Text size="sm" truncate>{p.autor ?? "—"}</Text></Table.Td>}
      <Table.Td><Text size="sm" fw={500} className="numero">{brl(p.valor_causa)}</Text></Table.Td>
      <Table.Td><SubsidiosTracos p={p} /></Table.Td>
      <Table.Td>
        {/* a recomendação depende do que a leitura dos autos achar; até lá a linha diz o que falta */}
        {p.extracao_pendente ? (
          <Group gap={6} wrap="nowrap">
            <Loader size={12} color="laranja" />
            <Text size="xs" c="dimmed">lendo documentos</Text>
          </Group>
        ) : (
          <>
            <TipoBadge tipo={p.recomendacao?.tipo} size="sm" />
            {p.recomendacao?.valor_sugerido != null && (
              <Text size="xs" c="dimmed" mt={2} className="numero">{brl(p.recomendacao.valor_sugerido)}</Text>
            )}
          </>
        )}
        {p.mais_dados_recomendado && (
          // Aviso em uma linha para as alturas de linha não variarem; o texto inteiro fica no tooltip.
          <Tooltip label="O modelo precisa de mais dados para uma recomendação mais segura." multiline w={240} withArrow>
            <Text fz={10} c="dimmed" mt={2} style={{ cursor: "help" }}>* precisa de mais dados</Text>
          </Tooltip>
        )}
      </Table.Td>
      <Table.Td>
        <StatusBadge status={p.status} size="sm" />
        {p.decisao_tipo && <Text size="xs" c="dimmed" mt={2}>decidiu {p.decisao_tipo}</Text>}
      </Table.Td>
      {gestor && <Table.Td><Text size="sm" truncate>{p.escritorio}</Text></Table.Td>}
    </Table.Tr>
  );
}
