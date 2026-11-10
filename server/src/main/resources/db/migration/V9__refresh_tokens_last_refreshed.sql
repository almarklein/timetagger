-- Refresh tokens no longer rotate; a session's one token records its latest use instead.
ALTER TABLE refresh_tokens ADD COLUMN last_refreshed_at TIMESTAMPTZ;
