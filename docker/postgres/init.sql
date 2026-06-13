-- PersonalJobSeeker — PostgreSQL Initialization
-- Runs once when the postgres container is first created.

-- Required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";     -- gen UUID v4
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid(), crypt()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- trigram similarity for job description search
CREATE EXTENSION IF NOT EXISTS "unaccent";      -- accent-insensitive search

-- Set timezone
SET timezone = 'UTC';
