/**
 * Singleton multiplexed WebSocket client.
 *
 * - One WebSocket is shared across the whole app.
 * - Components call useTickerStream(symbols) to subscribe; unsubscription
 *   happens on unmount via a refcount map.
 * - Incoming ticks are buffered and flushed into the Zustand tickerStore
 *   every 500ms (one batched setState per interval) — client-side throttle
 *   that keeps React renders cheap even if the server pushes faster.
 * - Alert frames are handed to a separate callback.
 */

import { useEffect } from "react";
import { useTickerStore } from "../stores/tickerStore";
import { getAuthToken, useAuthStore } from "../stores/authStore";

type TickMsg = { type: "tick"; symbol: string; price: number; ts: number };
type AlertMsg = {
  type: "alert";
  alertId: number;
  symbol: string;
  condition: string;
  threshold: number;
  price: number;
};
type ErrorMsg = { type: "error"; message: string };
type ServerMsg = TickMsg | AlertMsg | ErrorMsg;

type AlertHandler = (alert: AlertMsg) => void;

const FLUSH_INTERVAL_MS = 500;
const WS_PATH = "/ws";

let socket: WebSocket | null = null;
let connecting = false;
let reconnectDelay = 1000;
const refcount = new Map<string, number>();
const pendingSubscribe: Set<string> = new Set();
const tickBuffer: { symbol: string; price: number; ts: number }[] = [];
const alertHandlers: Set<AlertHandler> = new Set();
let flushTimer: number | null = null;

function wsUrl(): string | null {
  const token = getAuthToken();
  if (!token) return null;
  const baseUrl = import.meta.env.VITE_API_URL || "";
  const base = baseUrl
    ? baseUrl.replace(/^http/, "ws")
    : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;
  return `${base}${WS_PATH}?token=${encodeURIComponent(token)}`;
}

function ensureSocket(): void {
  if (socket && socket.readyState <= 1) return;
  if (connecting) return;
  const url = wsUrl();
  if (!url) return; // not authenticated yet
  connecting = true;
  const ws = new WebSocket(url);
  socket = ws;
  ws.addEventListener("open", () => {
    connecting = false;
    reconnectDelay = 1000;
    const all = Array.from(refcount.keys());
    if (all.length > 0) {
      ws.send(JSON.stringify({ action: "subscribe", symbols: all }));
    }
    // Send any that accumulated while disconnected
    pendingSubscribe.clear();
  });
  ws.addEventListener("message", (evt) => {
    let msg: ServerMsg;
    try {
      msg = JSON.parse(typeof evt.data === "string" ? evt.data : "") as ServerMsg;
    } catch {
      return;
    }
    if (msg.type === "tick") {
      tickBuffer.push({ symbol: msg.symbol, price: msg.price, ts: msg.ts });
    } else if (msg.type === "alert") {
      alertHandlers.forEach((h) => h(msg));
    }
  });
  const scheduleReconnect = (evt?: CloseEvent) => {
    connecting = false;
    socket = null;
    // 1008 = policy violation (bad/missing token). Don't reconnect — log out.
    if (evt && evt.code === 1008) {
      useAuthStore.getState().logout();
      return;
    }
    setTimeout(() => ensureSocket(), reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 15000);
  };
  ws.addEventListener("close", scheduleReconnect);
  ws.addEventListener("error", () => {
    try {
      ws.close();
    } catch {
      // ignore
    }
  });
}

function startFlushLoop(): void {
  if (flushTimer !== null) return;
  flushTimer = window.setInterval(() => {
    if (tickBuffer.length === 0) return;
    const batch = tickBuffer.splice(0, tickBuffer.length);
    useTickerStore.getState().applyBatch(batch);
  }, FLUSH_INTERVAL_MS);
}

function sendSubscribe(symbols: string[]): void {
  if (symbols.length === 0) return;
  if (socket && socket.readyState === 1) {
    socket.send(JSON.stringify({ action: "subscribe", symbols }));
  } else {
    symbols.forEach((s) => pendingSubscribe.add(s));
  }
}

function sendUnsubscribe(symbols: string[]): void {
  if (symbols.length === 0) return;
  if (socket && socket.readyState === 1) {
    socket.send(JSON.stringify({ action: "unsubscribe", symbols }));
  }
}

export function useTickerStream(symbols: string[]): void {
  useEffect(() => {
    ensureSocket();
    startFlushLoop();
    const toSub: string[] = [];
    for (const raw of symbols) {
      const s = raw.toUpperCase();
      const prev = refcount.get(s) ?? 0;
      refcount.set(s, prev + 1);
      if (prev === 0) toSub.push(s);
    }
    sendSubscribe(toSub);
    return () => {
      const toUnsub: string[] = [];
      for (const raw of symbols) {
        const s = raw.toUpperCase();
        const prev = refcount.get(s) ?? 0;
        if (prev <= 1) {
          refcount.delete(s);
          toUnsub.push(s);
        } else {
          refcount.set(s, prev - 1);
        }
      }
      sendUnsubscribe(toUnsub);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbols.join(",")]);
}

export function onAlert(handler: AlertHandler): () => void {
  alertHandlers.add(handler);
  return () => {
    alertHandlers.delete(handler);
  };
}

// Close the shared socket whenever the auth token changes so a fresh login
// reconnects under the new identity.
let lastToken: string | null = useAuthStore.getState().token;
useAuthStore.subscribe((state) => {
  if (state.token !== lastToken) {
    lastToken = state.token;
    if (socket) {
      try {
        socket.close();
      } catch {
        // ignore
      }
      socket = null;
    }
    if (state.token && refcount.size > 0) {
      ensureSocket();
    }
  }
});
