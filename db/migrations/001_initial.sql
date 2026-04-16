-- 001_initial.sql — MVP schema for astroturf detection + comment clustering.

CREATE TABLE IF NOT EXISTS comments (
    comment_id   VARCHAR PRIMARY KEY,
    docket_id    VARCHAR NOT NULL,
    posted_date  VARCHAR,
    submitter_name VARCHAR,
    comment_text VARCHAR,
    fetched_at   TIMESTAMPTZ,
    embedding    FLOAT[384]
);

CREATE TABLE IF NOT EXISTS duplicate_groups (
    group_id            INTEGER PRIMARY KEY,
    comment_ids         VARCHAR[],
    group_size          INTEGER NOT NULL,
    unique_submitters   INTEGER NOT NULL,
    campaign_likelihood DOUBLE  NOT NULL,
    is_astroturf        BOOLEAN NOT NULL,
    template_text       VARCHAR
);

CREATE TABLE IF NOT EXISTS comment_clusters (
    comment_id VARCHAR NOT NULL,
    docket_id  VARCHAR NOT NULL,
    cluster_id INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_comments_docket ON comments (docket_id);
CREATE INDEX IF NOT EXISTS idx_clusters_docket ON comment_clusters (docket_id);
CREATE INDEX IF NOT EXISTS idx_clusters_cluster ON comment_clusters (cluster_id);
CREATE INDEX IF NOT EXISTS idx_groups_astroturf ON duplicate_groups (is_astroturf);
