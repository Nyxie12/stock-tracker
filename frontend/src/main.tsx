import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import App from "./App";
import { setTokenGetter } from "./api/client";
import { getAuthToken, useAuthStore } from "./stores/authStore";

// Wire the api client to the auth store and start hydrating a stored token.
setTokenGetter(getAuthToken);
window.addEventListener("auth:logout", () => {
  useAuthStore.getState().logout();
});
void useAuthStore.getState().hydrate();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
