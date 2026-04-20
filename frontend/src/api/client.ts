import type {
  AstroturfSummary,
  ClusterComment,
  ClusterSummary,
  DuplicateGroupListResponse,
  GraphResponse,
} from "../types/api";

const API_BASE = "/api/v1";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function getAstroturfSummary(): Promise<AstroturfSummary> {
  return fetchJson<AstroturfSummary>("/astroturf/summary");
}

export function getDuplicateGroups(
  astroturfOnly = false,
  limit = 50,
  offset = 0,
): Promise<DuplicateGroupListResponse> {
  const params = new URLSearchParams({
    astroturf_only: String(astroturfOnly),
    limit: String(limit),
    offset: String(offset),
  });
  return fetchJson<DuplicateGroupListResponse>(
    `/astroturf/groups?${params.toString()}`,
  );
}

export function getClustersByDocket(
  docketId: string,
): Promise<ClusterSummary[]> {
  return fetchJson<ClusterSummary[]>(
    `/clusters/${encodeURIComponent(docketId)}`,
  );
}

export function getCitationGraph(docketId: string): Promise<GraphResponse> {
  return fetchJson<GraphResponse>(
    `/graph/${encodeURIComponent(docketId)}`,
  );
}

export function getGroupComments(
  groupId: number,
  limit = 50,
): Promise<ClusterComment[]> {
  return fetchJson<ClusterComment[]>(
    `/astroturf/groups/${groupId}/comments?limit=${limit}`,
  );
}

export function getClusterComments(
  docketId: string,
  clusterId: number,
  limit = 50,
): Promise<ClusterComment[]> {
  return fetchJson<ClusterComment[]>(
    `/clusters/${encodeURIComponent(docketId)}/${clusterId}?limit=${limit}`,
  );
}
