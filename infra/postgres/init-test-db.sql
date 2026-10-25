-- Runs once, on first container start, as part of Postgres initdb.
-- POSTGRES_DB already created the "kinfold" database; this adds "kinfold_test"
-- and enables pgvector in both, for local development only.

CREATE DATABASE kinfold_test;

\connect kinfold
CREATE EXTENSION IF NOT EXISTS vector;

\connect kinfold_test
CREATE EXTENSION IF NOT EXISTS vector;
