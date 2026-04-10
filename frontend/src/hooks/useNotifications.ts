import { useEffect, useState } from "react";
import { onAlert } from "./useTickerStream";
import { useAlertStore } from "../stores/alertStore";

export type NotificationPermissionState = "default" | "granted" | "denied" | "unsupported";

export function getPermissionState(): NotificationPermissionState {
  if (typeof Notification === "undefined") return "unsupported";
  return Notification.permission as NotificationPermissionState;
}

export async function requestPermission(): Promise<NotificationPermissionState> {
  if (typeof Notification === "undefined") return "unsupported";
  const result = await Notification.requestPermission();
  return result as NotificationPermissionState;
}

/**
 * Subscribes to alert frames from the WS stream and:
 *   - always appends to the alertStore recent-ring,
 *   - fires a browser Notification if permission is granted and the tab is hidden,
 *   - caller is responsible for rendering in-app toasts from the alertStore.
 */
export function useAlertListener(): NotificationPermissionState {
  const [permission, setPermission] = useState<NotificationPermissionState>(getPermissionState());
  const push = useAlertStore((s) => s.push);

  useEffect(() => {
    setPermission(getPermissionState());
    return onAlert((alert) => {
      const firedAt = Date.now();
      push({
        alertId: alert.alertId,
        symbol: alert.symbol,
        condition: alert.condition,
        threshold: alert.threshold,
        price: alert.price,
        firedAt,
      });
      if (
        typeof Notification !== "undefined" &&
        Notification.permission === "granted" &&
        document.visibilityState !== "visible"
      ) {
        try {
          new Notification(`${alert.symbol} ${alert.condition} ${alert.threshold}`, {
            body: `Price: ${alert.price.toFixed(2)}`,
            tag: `alert-${alert.alertId}`,
          });
        } catch {
          // ignore
        }
      }
    });
  }, [push]);

  return permission;
}
