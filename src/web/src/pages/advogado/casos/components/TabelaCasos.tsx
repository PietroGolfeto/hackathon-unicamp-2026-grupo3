import { Paper, Skeleton, Table, Text } from "@mantine/core";
import { useNavigate } from "react-router";

import type { ProcessoResumo } from "../../../../api/client";
import { CabecalhoColuna } from "./CabecalhoColuna";
import { LinhaCaso } from "./LinhaCaso";

export function TabelaCasos({ casos, gestor, temAutor, colunas, carregando }: {
  casos: ProcessoResumo[]; gestor: boolean; temAutor: boolean; colunas: number; carregando: boolean;
}) {
  const navigate = useNavigate();
  return (
    <Paper withBorder style={{ overflow: "hidden" }}>
      <Table.ScrollContainer minWidth={760}>
        <Table verticalSpacing="sm" horizontalSpacing="md" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <CabecalhoColuna>Processo</CabecalhoColuna>
              {temAutor && <CabecalhoColuna>Autor</CabecalhoColuna>}
              <CabecalhoColuna alinhar="right">Valor da causa</CabecalhoColuna>
              <CabecalhoColuna>Subsídios</CabecalhoColuna>
              <CabecalhoColuna>Recomendação</CabecalhoColuna>
              <CabecalhoColuna>Situação</CabecalhoColuna>
              {gestor && <CabecalhoColuna>Escritório</CabecalhoColuna>}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody className={carregando ? undefined : "escalonado"}>
            {carregando && Array.from({ length: 8 }).map((_, i) => (
              <Table.Tr key={i}>
                <Table.Td colSpan={colunas}><Skeleton height={34} radius="sm" /></Table.Td>
              </Table.Tr>
            ))}
            {casos.map((p) => (
              <LinhaCaso key={p.id} p={p} gestor={gestor} temAutor={temAutor} onSelecionar={(id) => navigate(`/casos/${id}`)} />
            ))}
            {!carregando && casos.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={colunas}>
                  <Text className="serif" c="dimmed" ta="center" py="xl" fz="lg">Nenhum processo encontrado.</Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Paper>
  );
}
