-- 003_citations.sql — store regulatory citations extracted from comments.

CREATE TABLE IF NOT EXISTS citations (
    comment_id    VARCHAR NOT NULL,
    docket_id     VARCHAR NOT NULL,
    citation_text VARCHAR NOT NULL,
    citation_type VARCHAR NOT NULL,   -- 'CFR' or 'USC'
    cfr_title     INTEGER,
    cfr_part      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_citations_docket   ON citations (docket_id);
CREATE INDEX IF NOT EXISTS idx_citations_cfr      ON citations (cfr_title, cfr_part);
