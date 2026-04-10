import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, BellOff, Trash2 } from "lucide-react";
import AlertForm from "../components/AlertForm";
import { alertsApi, type Alert } from "../api/alerts";
import { requestPermission, useAlertListener } from "../hooks/useNotifications";
import { useAlertStore } from "../stores/alertStore";
import { formatPrice } from "../lib/format";

export default function AlertsPage() {
  const qc = useQueryClient();
  const permission = useAlertListener();
  const recent = useAlertStore((s) => s.recent);

  const query = useQuery<Alert[]>({
    queryKey: ["alerts"],
    queryFn: alertsApi.list,
  });

  const create = useMutation({
    mutationFn: alertsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => alertsApi.setActive(id, active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => alertsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Alerts</h1>
        {permission !== "granted" && permission !== "unsupported" && (
          <button
            onClick={async () => {
              await requestPermission();
            }}
            className="rounded border border-emerald-500 px-3 py-1 text-xs text-emerald-400 hover:bg-emerald-500 hover:text-zinc-950"
          >
            Enable browser notifications
          </button>
        )}
      </div>
      <AlertForm onSubmit={(p) => create.mutate(p)} pending={create.isPending} />

      <div className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Active</h2>
        {query.data && query.data.length === 0 && (
          <div className="rounded border border-zinc-800 bg-zinc-900/40 p-4 text-sm text-zinc-400">
            No alerts yet.
          </div>
        )}
        <ul className="divide-y divide-zinc-800 rounded border border-zinc-800">
          {query.data?.map((a) => (
            <li key={a.id} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3 font-mono text-sm">
                {a.active ? (
                  <Bell className="h-4 w-4 text-emerald-400" />
                ) : (
                  <BellOff className="h-4 w-4 text-zinc-500" />
                )}
                <span className="font-semibold">{a.symbol}</span>
                <span className="text-zinc-400">{a.condition}</span>
                <span>{formatPrice(a.threshold)}</span>
                {a.last_triggered_at && (
                  <span className="text-xs text-zinc-500">
                    last fired {new Date(a.last_triggered_at).toLocaleString()}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggle.mutate({ id: a.id, active: !a.active })}
                  className="rounded border border-zinc-800 px-2 py-1 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
                >
                  {a.active ? "Disable" : "Enable"}
                </button>
                <button
                  onClick={() => remove.mutate(a.id)}
                  className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-rose-400"
                  aria-label="Remove"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Recent fires</h2>
        {recent.length === 0 && <div className="text-sm text-zinc-500">Nothing yet.</div>}
        <ul className="space-y-1 font-mono text-sm">
          {recent.map((f) => (
            <li key={`${f.alertId}-${f.firedAt}`} className="text-zinc-300">
              <span className="text-zinc-500">{new Date(f.firedAt).toLocaleTimeString()}</span>{" "}
              <span className="font-semibold">{f.symbol}</span> crossed {f.condition}{" "}
              {formatPrice(f.threshold)} @ {formatPrice(f.price)}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
