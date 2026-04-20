import type {
  AstroturfSummary,
  ClusterComment,
  ClusterSummary,
  DocketListResponse,
  DuplicateGroupListResponse,
  GraphResponse,
  QueryResponse,
} from "../types/api";

const API_BASE = "/api/v1";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }
  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function getDockets(q?: string, limit = 8): Promise<DocketListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (q) params.set("q", q);
  return fetchJson<DocketListResponse>(`/dockets?${params.toString()}`);
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

export function postQuery(
  docketId: string,
  question: string,
  topK = 10,
): Promise<QueryResponse> {
  return postJson<QueryResponse>("/query", {
    docket_id: docketId,
    question,
    top_k: topK,
  });
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
