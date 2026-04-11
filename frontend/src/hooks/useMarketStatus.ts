import { useQuery } from "@tanstack/react-query";
import { paperApi, type MarketStatus } from "../api/paper";

export function useMarketStatus() {
  return useQuery<MarketStatus>({
    queryKey: ["paper", "market-status"],
    queryFn: paperApi.marketStatus,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function sessionLabel(s: MarketStatus["session"]): string {
  switch (s) {
    case "pre":
      return "Pre-Market";
    case "regular":
      return "Market Open";
    case "post":
      return "After-Hours";
    case "closed":
    default:
      return "Closed";
  }
}
