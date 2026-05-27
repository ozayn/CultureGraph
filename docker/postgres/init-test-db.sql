-- Separate database for pytest (created once on first Docker Postgres init).
SELECT 'CREATE DATABASE culturegraph_test OWNER culturegraph'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'culturegraph_test')\gexec
