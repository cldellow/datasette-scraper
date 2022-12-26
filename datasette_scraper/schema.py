current_schema_version = 1000000;

schema = """
PRAGMA user_version = {};
""".format(current_schema_version) + """

-- Global rate limits. Currently, no attempt at fairness - a run of
-- a crawl can starve runs of other crawls.
CREATE TABLE _dss_host_rate_limit(
  host text primary key,
  next_fetch_at text not null default '2000-12-00 00:00:00.000',
  delay_seconds integer not null default 10
);

-- A cache of fetched pages. This may need to exist outside of
-- the schema migration code if we adopt https://github.com/phiresky/sqlite-zstd
CREATE TABLE _dss_fetch_cache(
  url text not null,
  fetched_at text not null,
  host text not null,
  request_headers text not null,
  status_code integer not null,
  response_headers text not null,
  body blob
);

-- The definition of a crawl, eg "Crawl every page at most 3 hops away from
-- news.ycombinator.com"
CREATE TABLE _dss_crawl(
  id integer primary key,
  name text not null,
  config text not null
);

-- A specific attempt to perform a crawl
CREATE TABLE _dss_job(
  id integer primary key,
  crawl_id integer not null,
  started_at text not null,
  -- NULL finished-at => currently in progress
  finished_at text
);

-- URLs to be crawled
CREATE TABLE _dss_crawl_queue(
  job_id integer not null,
  host text not null,
  url text not null,
  depth integer not null
);

-- URLs that were crawled
CREATE TABLE _dss_crawl_queue_history(
  job_id integer not null,
  host text not null,
  url text not null,
  fetched_at text not null,
  fetched_fresh boolean not null,
  depth integer not null,
  status_code integer not null,
  content_type text not null,
  size integer not null
);

-- Metrics on a specific crawl
CREATE TABLE _dss_job_stats(
  job_id integer not null,
  host text not null,
  fetched integer not null default 0,
  fetched_fresh integer not null default 0,
  fetched_2xx integer not null default 0,
  fetched_3xx integer not null default 0,
  fetched_4xx integer not null default 0,
  fetched_5xx integer not null default 0
);

CREATE TABLE _dss_extract_stats(
  job_id integer not null,
  database text not null,
  tbl text not null,
  added integer not null default 0,
  modified integer not null default 0,
  same integer not null default 0
);
"""
