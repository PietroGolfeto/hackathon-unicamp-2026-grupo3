import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "./theme.css";

import {
  Badge, Button, Card, MantineProvider, Modal, Paper, Tooltip, createTheme, rem, type MantineColorsTuple,
} from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import App from "./App";

// Identidade visual da Enter (decisão 29): neutros quentes, tinta quase preta e laranja como acento.
// A posição 6 de cada escala é o tom de marca: é ela que o Mantine usa em filled, light e outline.
const tinta: MantineColorsTuple = ["#f3f3f3", "#e6e6e6", "#d0d0d0", "#b0b0b0", "#8a8a8a", "#5d5d5d", "#171717", "#2b2b2b", "#0f0f0f", "#000000"];
const laranja: MantineColorsTuple = ["#fff7e8", "#ffefd1", "#ffe2b0", "#ffd28a", "#ffc36a", "#ffb84f", "#ffae35", "#f2a022", "#dd8f14", "#b8740c"];
const verde: MantineColorsTuple = ["#e8f8ec", "#cfefd7", "#aee4bc", "#88d69d", "#63c980", "#3bbb5e", "#18ad3a", "#139432", "#0f7a2a", "#0b5f20"];
const vermelho: MantineColorsTuple = ["#fdeaec", "#fbd2d7", "#f7adb5", "#f28592", "#ee5f70", "#ec4a5d", "#ea384c", "#d02c3f", "#b12334", "#8c1a28"];
const gray: MantineColorsTuple = ["#f3f3f3", "#e9e9e9", "#dcdcdc", "#cecece", "#b3b3b3", "#8f8f8f", "#6b6b6b", "#3c3c3c", "#262626", "#171717"];

const theme = createTheme({
  fontFamily: "Geist, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  fontFamilyMonospace: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
  headings: {
    fontFamily: "'Noto Serif', Georgia, 'Times New Roman', serif",
    fontWeight: "400",
    sizes: {
      h1: { fontSize: rem(40), lineHeight: "1.12", fontWeight: "300" },
      h2: { fontSize: rem(30), lineHeight: "1.2", fontWeight: "300" },
      h3: { fontSize: rem(24), lineHeight: "1.25" },
      h4: { fontSize: rem(19), lineHeight: "1.3" },
    },
  },
  colors: { tinta, laranja, verde, vermelho, gray },
  primaryColor: "tinta",
  primaryShade: 6,
  black: "#171717",
  autoContrast: true,
  luminanceThreshold: 0.45,
  defaultRadius: "md",
  cursorType: "pointer",
  respectReducedMotion: true,
  components: {
    Paper: Paper.extend({ defaultProps: { radius: 12 } }),
    Card: Card.extend({ defaultProps: { radius: 12, withBorder: true, padding: "lg" } }),
    Button: Button.extend({ defaultProps: { radius: 6 } }),
    Badge: Badge.extend({
      defaultProps: { radius: "sm" },
      styles: { root: { textTransform: "none", fontWeight: 500, letterSpacing: 0 } },
    }),
    Modal: Modal.extend({
      defaultProps: {
        radius: 12, centered: true,
        overlayProps: { backgroundOpacity: 0.4, blur: 3 },
        transitionProps: { transition: "pop", duration: 180 },
      },
    }),
    Tooltip: Tooltip.extend({ defaultProps: { radius: "sm", transitionProps: { transition: "fade-up", duration: 150 } } }),
  },
});

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 10_000 } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider theme={theme}>
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
);
