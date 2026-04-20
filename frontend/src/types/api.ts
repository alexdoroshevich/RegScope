export interface AstroturfSummary {
  total_groups: number;
  astroturf_groups: number;
  total_flagged_comments: number;
  max_campaign_likelihood: number;
}

export interface DuplicateGroup {
  group_id: number;
  comment_ids: string[];
  group_size: number;
  unique_submitters: number;
  campaign_likelihood: number;
  is_astroturf: boolean;
  template_text: string | null;
}

export interface DuplicateGroupListResponse {
  items: DuplicateGroup[];
  total: number;
  limit: number;
  offset: number;
}

export interface ClusterSummary {
  cluster_id: number;
  comment_count: number;
  label: string | null;
  summary: string | null;
}

export interface ClusterComment {
  comment_id: string;
  comment_text: string | null;
  submitter_name: string | null;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  count: number;
  citation_type?: string;
}

export interface GraphLink {
  source: string;
  target: string;
  value: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface SourceComment {
  comment_id: string;
  docket_id: string;
  comment_text: string;
  similarity: number;
}

export interface QueryResponse {
  question: string;
  answer: string;
  sources: SourceComment[];
  model: string;
  cost_usd: number;
  from_cache: boolean;
}
