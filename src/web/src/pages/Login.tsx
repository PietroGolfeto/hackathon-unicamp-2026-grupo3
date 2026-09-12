import { Alert, Button, Center, Paper, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";

import { api } from "../api/client";
import { homeDe, useSession } from "../auth/useSession";

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
    <Center mih="100vh" p="md">
      <Paper withBorder p="lg" radius="md" w="100%" maw={380}>
        <form onSubmit={(e) => { e.preventDefault(); login.mutate(); }}>
          <Stack>
            <div>
              <Title order={3}>Política de Acordos</Title>
              <Text c="dimmed" size="sm">Banco UFMG · empréstimo não reconhecido</Text>
            </div>
            <TextInput label="E-mail" value={email} onChange={(e) => setEmail(e.currentTarget.value)}
              autoComplete="username" required autoFocus inputMode="email" />
            <PasswordInput label="Senha" value={senha} onChange={(e) => setSenha(e.currentTarget.value)}
              autoComplete="current-password" required />
            {login.isError && <Alert color="red" variant="light">{(login.error as Error).message}</Alert>}
            <Button type="submit" loading={login.isPending} fullWidth>Entrar</Button>
            <Text size="xs" c="dimmed">
              Demonstração: <b>adv1@escritorio-a</b> (advogado) ou <b>gestor@banco-ufmg</b> (gestor), senha <b>senha123</b>.
            </Text>
          </Stack>
        </form>
      </Paper>
    </Center>
  );
}
