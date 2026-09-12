import { AppShell, Badge, Button, Container, Group, Text } from "@mantine/core";
import { Link, Outlet, useLocation } from "react-router";

import { useLogout, useSession } from "../auth/useSession";

const LINKS_ADV = [{ to: "/casos", rotulo: "Casos" }];
const LINKS_GESTOR = [
  { to: "/gestor/painel", rotulo: "Painel" },
  { to: "/gestor/politica", rotulo: "Política" },
  { to: "/gestor/aprovacoes", rotulo: "Aprovações" },
  { to: "/casos", rotulo: "Casos" },
];

export function Layout() {
  const { data: usuario } = useSession();
  const logout = useLogout();
  const { pathname } = useLocation();
  const links = usuario?.papel === "gestor" ? LINKS_GESTOR : LINKS_ADV;
  return (
    <AppShell header={{ height: 56 }} padding="md">
      <AppShell.Header>
        <Container size="xl" h="100%">
          <Group h="100%" justify="space-between" wrap="nowrap" gap="xs">
            <Group gap="xs" wrap="nowrap">
              <Text fw={700} size="sm" component={Link} to="/" c="indigo" style={{ textDecoration: "none" }}>
                Acordos · Banco UFMG
              </Text>
              <Group gap={4} visibleFrom="xs">
                {links.map((l) => (
                  <Button
                    key={l.to} component={Link} to={l.to} size="compact-sm"
                    variant={pathname.startsWith(l.to) ? "light" : "subtle"}
                  >
                    {l.rotulo}
                  </Button>
                ))}
              </Group>
            </Group>
            <Group gap="xs" wrap="nowrap">
              {usuario && (
                <Text size="xs" c="dimmed" visibleFrom="sm" truncate maw={220}>
                  {usuario.nome}{usuario.escritorio_nome ? ` · ${usuario.escritorio_nome}` : ""}
                </Text>
              )}
              {usuario?.papel === "gestor" && <Badge size="sm" variant="outline">gestor</Badge>}
              <Button size="compact-sm" variant="default" onClick={() => logout.mutate()} loading={logout.isPending}>
                Sair
              </Button>
            </Group>
          </Group>
        </Container>
      </AppShell.Header>
      <AppShell.Main>
        <Container size="xl" px={{ base: 0, sm: "md" }}>
          <Group gap={4} hiddenFrom="xs" mb="sm">
            {links.map((l) => (
              <Button key={l.to} component={Link} to={l.to} size="compact-xs" variant={pathname.startsWith(l.to) ? "light" : "subtle"}>
                {l.rotulo}
              </Button>
            ))}
          </Group>
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
