-- 004_documents.sql — store Federal Register regulatory documents.
--
-- Populated by `db.init_db.load_documents` from year-partitioned Parquet
-- written by `data.ingest.federal_register.write_documents_parquet`.

CREATE TABLE IF NOT EXISTS documents (
    document_number   VARCHAR PRIMARY KEY,
    docket_id         VARCHAR,              -- first docket_ids entry, or NULL
    title             VARCHAR NOT NULL,
    doc_type          VARCHAR NOT NULL,     -- RULE | PRORULE | NOTICE | …
    abstract          VARCHAR,
    agency_names      VARCHAR,             -- JSON-encoded list, e.g. '["EPA"]'
    publication_date  VARCHAR,             -- YYYY-MM-DD string
    effective_on      VARCHAR,
    comments_close_on VARCHAR,
    html_url          VARCHAR,
    citation          VARCHAR,
    significant       BOOLEAN,
    fetched_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_documents_docket  ON documents (docket_id);
CREATE INDEX IF NOT EXISTS idx_documents_pubdate ON documents (publication_date);
CREATE INDEX IF NOT EXISTS idx_documents_doctype ON documents (doc_type);
