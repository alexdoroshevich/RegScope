-- 002_cluster_labels.sql — store LLM-generated labels for comment clusters.

CREATE TABLE IF NOT EXISTS cluster_labels (
    docket_id   VARCHAR NOT NULL,
    cluster_id  INTEGER NOT NULL,
    label       VARCHAR NOT NULL,
    summary     VARCHAR NOT NULL,
    prompt_hash VARCHAR NOT NULL,
    model       VARCHAR NOT NULL,
    cost_usd    DOUBLE  NOT NULL DEFAULT 0.0,
    created_at  TIMESTAMPTZ DEFAULT current_timestamp,
    PRIMARY KEY (docket_id, cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_cluster_labels_docket ON cluster_labels (docket_id);
