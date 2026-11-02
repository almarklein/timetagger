package timetagger.db

import kotliquery.Row
import kotliquery.Session
import kotliquery.queryOf
import java.time.Instant
import java.util.UUID

data class RefreshToken(
    val id: Long, val userId: Long, val familyId: UUID, val userAgent: String?,
    val createdAt: Instant, val expiresAt: Instant, val usedAt: Instant?, val revokedAt: Instant?,
)

/** Refresh tokens, looked up by the SHA-256 of the token; the token itself is never stored. */
class RefreshTokenRepository {
    private val select = "SELECT id, user_id, family_id, user_agent, created_at, expires_at, used_at, revoked_at FROM refresh_tokens"

    private fun token(row: Row) = RefreshToken(
        id = row.long("id"),
        userId = row.long("user_id"),
        familyId = row.uuid("family_id"),
        userAgent = row.stringOrNull("user_agent"),
        createdAt = row.instant("created_at"),
        expiresAt = row.instant("expires_at"),
        usedAt = row.instantOrNull("used_at"),
        revokedAt = row.instantOrNull("revoked_at"),
    )

    fun insert(session: Session, userId: Long, familyId: UUID, hash: String, userAgent: String?, expiresAt: Instant) {
        session.update(
            queryOf(
                "INSERT INTO refresh_tokens (user_id, family_id, token_hash, user_agent, expires_at) VALUES (?, ?, ?, ?, ?)",
                userId, familyId, hash, userAgent, expiresAt,
            ),
        )
    }

    /** Locks the row, so two refreshes racing with one token can't both succeed. */
    fun byHashForUpdate(session: Session, hash: String): RefreshToken? =
        session.single(queryOf("$select WHERE token_hash = ? FOR UPDATE", hash), ::token)

    fun markUsed(session: Session, id: Long) {
        session.update(queryOf("UPDATE refresh_tokens SET used_at = now() WHERE id = ?", id))
    }

    /** Revokes the family's still-unused tokens issued at or after [since]. */
    fun revokeUnusedSince(session: Session, familyId: UUID, since: Instant) {
        session.update(
            queryOf(
                "UPDATE refresh_tokens SET revoked_at = now() WHERE family_id = ? AND used_at IS NULL AND revoked_at IS NULL AND created_at >= ?",
                familyId, since,
            ),
        )
    }

    fun revokeFamily(session: Session, familyId: UUID) {
        session.update(queryOf("UPDATE refresh_tokens SET revoked_at = now() WHERE family_id = ? AND revoked_at IS NULL", familyId))
    }

    fun revokeFamily(session: Session, userId: Long, familyId: UUID): Boolean =
        session.update(
            queryOf("UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = ? AND family_id = ? AND revoked_at IS NULL", userId, familyId),
        ) > 0

    fun revokeAll(session: Session, userId: Long) {
        session.update(queryOf("UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = ? AND revoked_at IS NULL", userId))
    }

    /** The live token of each signed-in session, newest first. */
    fun liveSessions(session: Session, userId: Long): List<RefreshToken> =
        session.list(
            queryOf(
                "$select WHERE user_id = ? AND used_at IS NULL AND revoked_at IS NULL AND expires_at > now() ORDER BY created_at DESC",
                userId,
            ),
            ::token,
        )
}

data class ApiKey(
    val id: Long, val userId: Long, val name: String, val prefix: String,
    val createdAt: Instant, val lastUsedAt: Instant?,
)

/** API keys, looked up by the SHA-256 of the key; the key itself is shown once and never stored. */
class ApiKeyRepository {
    private val select = "SELECT id, user_id, name, prefix, created_at, last_used_at FROM api_keys"

    private fun key(row: Row) = ApiKey(
        id = row.long("id"),
        userId = row.long("user_id"),
        name = row.string("name"),
        prefix = row.string("prefix"),
        createdAt = row.instant("created_at"),
        lastUsedAt = row.instantOrNull("last_used_at"),
    )

    fun insert(session: Session, userId: Long, name: String, hash: String, prefix: String): ApiKey =
        session.single(
            queryOf(
                "INSERT INTO api_keys (user_id, name, key_hash, prefix) VALUES (?, ?, ?, ?) RETURNING id, user_id, name, prefix, created_at, last_used_at",
                userId, name, hash, prefix,
            ),
            ::key,
        )!!

    fun live(session: Session, userId: Long): List<ApiKey> =
        session.list(queryOf("$select WHERE user_id = ? AND revoked_at IS NULL ORDER BY created_at", userId), ::key)

    fun byHash(session: Session, hash: String): ApiKey? =
        session.single(queryOf("$select WHERE key_hash = ? AND revoked_at IS NULL", hash), ::key)

    /** Stamps the use at most once a minute, so a busy script doesn't write on every call. */
    fun touch(session: Session, id: Long) {
        session.update(
            queryOf("UPDATE api_keys SET last_used_at = now() WHERE id = ? AND (last_used_at IS NULL OR last_used_at < now() - interval '1 minute')", id),
        )
    }

    fun revoke(session: Session, userId: Long, id: Long): Boolean =
        session.update(queryOf("UPDATE api_keys SET revoked_at = now() WHERE user_id = ? AND id = ? AND revoked_at IS NULL", userId, id)) > 0
}
