current_schema_version = 1000003;

schema = """
PRAGMA user_version = {};
""".format(current_schema_version) + """

-- Site-specific dictionaries for zstd
CREATE TABLE dss_zstd_dict(
  id integer primary key,
  host text not null,
  active boolean not null default true,
  dict blob not null
);


-- Global rate limits. Currently, no attempt at fairness - a run of
-- a crawl can starve runs of other crawls.
CREATE TABLE dss_host_rate_limit(
  host text primary key,
  next_fetch_at text not null default (strftime('%Y-%m-%d %H:%M:%f')),
  delay_seconds integer not null default 10
);

-- A cache of fetched pages. This may need to exist outside of
-- the schema migration code if we adopt https://github.com/phiresky/sqlite-zstd
CREATE TABLE dss_fetch_cache(
  -- A hash of the request that was sent, eg url + headers
  request_hash text primary key,

  host text not null,

  -- The URL that was fetched
  url text not null,

  -- When this was fetched from an origin server. This will also be
  -- present in the object, but exposing it as a column makes it
  -- easier to prune old entries.
  fetched_at text not null default (strftime('%Y-%m-%d %H:%M:%f')),

  -- When this was last accessed via a crawl -- can be helpful for
  -- pruning entries that are no longer needed.
  read_at text not null default (strftime('%Y-%m-%d %H:%M:%f')),

  -- The response object; UTF-8 JSON encoded. Might be compressed.
  object blob not null,

  dict_id integer references dss_zstd_dict(id)
);

-- The definition of a crawl, eg "Crawl every page at most 3 hops away from
-- news.ycombinator.com"
CREATE TABLE dss_crawl(
  id integer primary key,
  name text not null,
  config text not null
);

-- A specific attempt to perform a crawl
CREATE TABLE dss_job(
  id integer primary key,
  crawl_id integer not null references dss_crawl(id) on delete cascade,
  started_at text not null default (strftime('%Y-%m-%d %H:%M:%f')),
  status text not null default 'seeding' check (status IN ('seeding', 'running', 'cancelled', 'done')),
  -- NULL finished-at => currently in progress
  finished_at text
);

-- URLs to be crawled
CREATE TABLE dss_crawl_queue(
  id integer primary key,
  job_id integer not null references dss_job(id) on delete cascade,
  host text not null,
  queued_at text not null default (strftime('%Y-%m-%d %H:%M:%f')),
  url text not null,
  depth integer not null,
  claimed_at text
);

-- URLs that were crawled
CREATE TABLE dss_crawl_queue_history(
  job_id integer not null references dss_job(id) on delete cascade,
  host text not null,
  url text not null,
  depth integer not null,
  processed_at text not null,
  fetched_fresh boolean not null,
  status_code integer,
  content_type text,
  size integer,
  duration integer,
  skipped_reason text,
  request_hash text references dss_fetch_cache(request_hash) on delete cascade,
  check (
    (skipped_reason is null and status_code is not null and size is not null and content_type is not null and duration is not null) or
    (skipped_reason is not null and status_code is null and size is null and content_type is null and duration is null)
  )
);

-- Metrics on a specific crawl
CREATE TABLE dss_job_stats(
  job_id integer not null references dss_job(id) on delete cascade,
  host text not null,
  fetched integer not null default 0,
  fetched_fresh integer not null default 0,
  fetched_2xx integer not null default 0,
  fetched_3xx integer not null default 0,
  fetched_4xx integer not null default 0,
  fetched_5xx integer not null default 0,
  primary key (job_id, host)
);

CREATE TABLE dss_extract_stats(
  job_id integer not null references dss_job(id) on delete cascade,
  database text not null,
  tbl text not null,
  inserted integer not null default 0,
  updated integer not null default 0,
  deleted integer not null default 0,
  primary key (job_id, database, tbl)
);

CREATE TABLE dss_ops(
  id integer primary key,
  queued_at text not null default (strftime('%Y-%m-%d %H:%M:%f')),
  finished_at text,
  type text not null,
  config text not null default '{}'
);

CREATE UNIQUE INDEX idx_only_one_active_job_per_crawl ON dss_job(crawl_id) WHERE finished_at IS NULL;

CREATE INDEX idx_crawl_queue_item ON dss_crawl_queue(job_id, url);
CREATE INDEX idx_crawl_queue_history_item ON dss_crawl_queue_history(job_id, url);
CREATE INDEX idx_dss_zstd_dict_host ON dss_zstd_dict(host);
CREATE INDEX idx_dss_fetch_cache_host ON dss_fetch_cache(host);
CREATE INDEX idx_crawl_queue_host_depth_queued_at ON dss_crawl_queue(host, depth, queued_at);
"""
