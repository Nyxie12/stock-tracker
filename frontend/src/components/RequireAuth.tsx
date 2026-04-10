import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

type Props = { children: ReactNode };

export default function RequireAuth({ children }: Props) {
  const status = useAuthStore((s) => s.status);
  const location = useLocation();

  if (status === "idle" || status === "loading") {
    return (
      <div className="flex h-full w-full items-center justify-center text-sm text-zinc-500">
        Loading...
      </div>
    );
  }

  if (status !== "authed") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
