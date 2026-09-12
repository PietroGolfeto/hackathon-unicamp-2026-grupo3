import {
  Alert, Box, Button, Center, Group, Paper, PasswordInput, SimpleGrid, Stack, Text, TextInput, Title, UnstyledButton,
} from "@mantine/core";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";

import { api } from "../api/client";
import { homeDe, useSession } from "../auth/useSession";
import { IcoSeta } from "../components/Icones";
import { Marca } from "../components/Marca";

const SENHA_DEMO = "senha123";
const ACESSOS_DEMO = [
  { rotulo: "Advogado", email: "adv1@escritorio-a", detalhe: "Escritório A · decide os casos" },
  { rotulo: "Gestor", email: "gestor@banco-ufmg", detalhe: "Banco UFMG · política e painel" },
];
const PILARES = [
  { titulo: "Regra de decisão", texto: "Acordo ou defesa pelo custo esperado de cada caminho, não por um limiar solto." },
  { titulo: "Valor sugerido", texto: "Oferta alvo e banda mínima e máxima, com os motivos em linguagem jurídica." },
  { titulo: "Aderência e efetividade", texto: "Cada decisão fica gravada contra a recomendação que o advogado viu." },
];

export default function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  const { data: sessao } = useSession();

  const login = useMutation({
    mutationFn: () => api.login(email, senha),
    onSuccess: (u) => {
      qc.setQueryData(["me"], u);
      const de = (location.state as { de?: string } | null)?.de;
      navigate(de && de !== "/login" ? de : homeDe(u), { replace: true });
    },
  });

  if (sessao) return <Navigate to={homeDe(sessao)} replace />;

  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing={0} mih="100vh">
      <Box visibleFrom="md" bg="tinta.6" p={{ md: 48, lg: 64 }} display="flex"
        style={{ flexDirection: "column", justifyContent: "space-between", gap: 48 }}>
        <div className="subir"><Marca invertida tamanho="lg" to={null} /></div>
        <Stack gap="lg" className="subir atraso-1" maw={520}>
          <Title order={1} c="white" fz={{ md: 40, lg: 48 }}>
            Uma política de acordos que o advogado{" "}
            <Text component="em" inherit c="laranja.6">vê antes</Text> de decidir.
          </Title>
          <Text c="rgba(255,255,255,.64)" size="md" lh={1.6}>
            Cinco mil processos por mês de empréstimo não reconhecido. Para cada um, uma recomendação a partir do custo
            esperado, gravada no momento em que o caso é aberto. O gestor mede aderência e efetividade sobre o que foi
            mostrado, não sobre o que se supõe.
          </Text>
        </Stack>
        <SimpleGrid cols={3} spacing="lg" className="escalonado">
          {PILARES.map((p) => (
            <div key={p.titulo}>
              <Box w={28} h={2} bg="laranja.6" mb="sm" style={{ borderRadius: 2 }} />
              <Text c="white" size="sm" fw={500}>{p.titulo}</Text>
              <Text c="rgba(255,255,255,.56)" size="xs" mt={4} lh={1.5}>{p.texto}</Text>
            </div>
          ))}
        </SimpleGrid>
      </Box>

      <Center p={{ base: "md", sm: "xl" }}>
        <Stack w="100%" maw={400} gap="lg" className="subir atraso-1">
          <Box hiddenFrom="md"><Marca to={null} /></Box>
          <div>
            <Title order={2}>Entrar</Title>
            <Text c="dimmed" size="sm" mt={4}>Política de acordos · Banco UFMG · empréstimo não reconhecido</Text>
          </div>
          <Paper withBorder p="lg">
            <form onSubmit={(e) => { e.preventDefault(); login.mutate(); }}>
              <Stack gap="md">
                <TextInput label="E-mail" value={email} onChange={(e) => setEmail(e.currentTarget.value)} size="md"
                  autoComplete="username" required autoFocus inputMode="email" placeholder="voce@escritorio" />
                <PasswordInput label="Senha" value={senha} onChange={(e) => setSenha(e.currentTarget.value)} size="md"
                  autoComplete="current-password" required placeholder="••••••••" />
                {login.isError && <Alert color="vermelho" variant="light" radius="md">{(login.error as Error).message}</Alert>}
                <Button type="submit" loading={login.isPending} fullWidth size="md" rightSection={<IcoSeta size={16} />}>
                  Entrar
                </Button>
              </Stack>
            </form>
          </Paper>
          <div>
            <Text size="xs" c="dimmed" fw={500} tt="uppercase" lts=".06em" mb="xs">Acesso de demonstração</Text>
            <SimpleGrid cols={2} spacing="xs">
              {ACESSOS_DEMO.map((a) => (
                <UnstyledButton key={a.email} onClick={() => { setEmail(a.email); setSenha(SENHA_DEMO); }}
                  className="cartao-hover" p="sm" bg="white"
                  style={{ border: "1px solid var(--enter-traco)", borderRadius: 10 }}>
                  <Group justify="space-between" wrap="nowrap">
                    <Text size="sm" fw={500}>{a.rotulo}</Text>
                    <IcoSeta size={14} style={{ color: "var(--enter-laranja)" }} />
                  </Group>
                  <Text size="xs" c="dimmed" mt={2}>{a.detalhe}</Text>
                </UnstyledButton>
              ))}
            </SimpleGrid>
            <Text size="xs" c="dimmed" mt="xs">Preenche e-mail e senha ({SENHA_DEMO}); basta confirmar.</Text>
          </div>
        </Stack>
      </Center>
    </SimpleGrid>
  );
}
