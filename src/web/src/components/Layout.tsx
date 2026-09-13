import { ActionIcon, AppShell, Box, Container, Group, SegmentedControl, Text, Tooltip, UnstyledButton } from "@mantine/core";
import { Link, Outlet, useLocation } from "react-router";

import type { Papel } from "../api/client";
import { useLogout, useSession, useTrocarPapel } from "../auth/useSession";
import { IcoSair } from "./Icones";
import { Marca } from "./Marca";

const LINKS_ADV = [{ to: "/casos", rotulo: "Casos" }];
const LINKS_GESTOR = [
  { to: "/gestor/painel", rotulo: "Painel" },
];

function LinkTopo({ to, rotulo, ativo }: { to: string; rotulo: string; ativo: boolean }) {
  return (
    <UnstyledButton component={Link} to={to} px="sm" h="100%" pos="relative" display="inline-flex" style={{ alignItems: "center" }}>
      <Text size="sm" fw={500} c={ativo ? "tinta.6" : "dimmed"} style={{ transition: "color .15s" }}>{rotulo}</Text>
      {ativo && (
        <Box className="crescer" pos="absolute" left="var(--mantine-spacing-sm)" right="var(--mantine-spacing-sm)" bottom={-1} h={2}
          bg="laranja.6" style={{ borderRadius: 2 }} />
      )}
    </UnstyledButton>
  );
}

export function Layout() {
  const { data: usuario } = useSession();
  const logout = useLogout();
  const trocar = useTrocarPapel();
  const { pathname } = useLocation();
  const links = usuario?.papel === "gestor" ? LINKS_GESTOR : LINKS_ADV;
  const ativo = (to: string) => pathname.startsWith(to);

  return (
    <AppShell header={{ height: 60 }} padding={{ base: "md", sm: "lg" }}>
      <AppShell.Header style={{ borderColor: "var(--enter-traco)" }}>
        <Container size="xl" h="100%">
          <Group h="100%" justify="space-between" wrap="nowrap" gap="md">
            <Group gap="lg" wrap="nowrap" h="100%">
              <Marca />
              <Group gap={0} wrap="nowrap" h="100%" visibleFrom="xs">
                {links.map((l) => <LinkTopo key={l.to} to={l.to} rotulo={l.rotulo} ativo={ativo(l.to)} />)}
              </Group>
            </Group>
            <Group gap="sm" wrap="nowrap">
              {usuario && (
                <SegmentedControl size="xs" disabled={trocar.isPending} value={usuario.papel}
                  onChange={(v) => trocar.mutate(v as Papel)}
                  data={[{ label: "Advogado", value: "advogado" }, { label: "Gestor", value: "gestor" }]} />
              )}
              <Tooltip label="Sair">
                <ActionIcon variant="subtle" color="tinta" size="lg" radius="xl" aria-label="Sair"
                  onClick={() => logout.mutate()} loading={logout.isPending}>
                  <IcoSair size={18} />
                </ActionIcon>
              </Tooltip>
            </Group>
          </Group>
        </Container>
      </AppShell.Header>
      <AppShell.Main>
        <Container size="xl" px={{ base: 0, sm: "md" }}>
          <Group gap={4} hiddenFrom="xs" mb="md">
            {links.map((l) => (
              <UnstyledButton key={l.to} component={Link} to={l.to} px="sm" py={6}
                bg={ativo(l.to) ? "white" : "transparent"}
                style={{ borderRadius: 6, border: `1px solid ${ativo(l.to) ? "var(--enter-traco-forte)" : "transparent"}` }}>
                <Text size="sm" fw={500} c={ativo(l.to) ? "tinta.6" : "dimmed"}>{l.rotulo}</Text>
              </UnstyledButton>
            ))}
          </Group>
          <div key={pathname} className="subir">
            <Outlet />
          </div>
          <Text size="xs" c="dimmed" ta="center" mt={48} pb="md">
            Banco Unicamp · Política de acordos · empréstimo não reconhecido
          </Text>
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
