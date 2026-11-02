package timetagger.auth

import com.auth0.jwt.JWT
import com.auth0.jwt.algorithms.Algorithm
import com.auth0.jwt.exceptions.JWTVerificationException
import org.slf4j.LoggerFactory
import timetagger.ApiException
import timetagger.db.ApiKey
import timetagger.db.ApiKeyRepository
import timetagger.db.Database
import timetagger.db.RefreshToken
import timetagger.db.RefreshTokenRepository
import timetagger.db.UserRepository
import io.ktor.http.HttpStatusCode
import java.security.MessageDigest
import java.security.SecureRandom
import java.time.Duration
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.Base64
import java.util.UUID

private val log = LoggerFactory.getLogger("timetagger.auth")

/** How a request proved who it is. */
enum class AuthKind { ACCESS_TOKEN, API_KEY }

/** The authenticated user. */
data class AuthInfo(val userId: Long, val username: String, val kind: AuthKind)

/** A fresh access token and the refresh token that gets the next one. */
data class TokenPair(val accessToken: String, val accessExpiresAt: Instant, val refreshToken: String, val refreshExpiresAt: Instant)

class Unauthorized(message: String) : ApiException(HttpStatusCode.Unauthorized, "unauthorized", message)

/** Signs and checks the short-lived HS256 access tokens. Nothing about them is stored. */
class AccessTokens(key: String, private val lifetime: Duration = Duration.ofMinutes(15)) {
    private val algorithm = Algorithm.HMAC256(
        key.trim().ifEmpty {
            log.warn("TIMETAGGER_JWT_KEY is not set; using an ephemeral key. Access tokens die with a restart; refresh tokens survive.")
            Secrets.random(32)
        },
    )
    private val verifier = JWT.require(algorithm).build()

    fun issue(userId: Long, username: String): Pair<String, Instant> {
        val now = Instant.now().truncatedTo(ChronoUnit.SECONDS)
        val expiresAt = now.plus(lifetime)
        return JWT.create()
            .withSubject(username)
            .withClaim("uid", userId)
            .withIssuedAt(now)
            .withExpiresAt(expiresAt)
            .withJWTId(UUID.randomUUID().toString())
            .sign(algorithm) to expiresAt
    }

    /** The token's user, or null if the signature or expiry is wrong. */
    fun verify(token: String): AuthInfo? = try {
        val jwt = verifier.verify(token)
        AuthInfo(jwt.getClaim("uid").asLong() ?: return null, jwt.subject ?: return null, AuthKind.ACCESS_TOKEN)
    } catch (_: JWTVerificationException) {
        null
    }
}

object Secrets {
    private val random = SecureRandom()

    fun random(bytes: Int): String =
        Base64.getUrlEncoder().withoutPadding().encodeToString(ByteArray(bytes).also(random::nextBytes))

    /** Refresh tokens and API keys are high-entropy, so a plain SHA-256 is enough to store them by. */
    fun hash(secret: String): String =
        MessageDigest.getInstance("SHA-256").digest(secret.toByteArray()).joinToString("") { "%02x".format(it) }
}

/**
 * Logins, refresh-token rotation and API keys. A login starts a refresh-token family;
 * each refresh retires its token and issues the next. A retired token coming back
 * means it was copied, so the whole family is revoked.
 */
class AuthService(
    private val db: Database,
    private val users: UserRepository,
    private val passwords: PasswordService,
    private val access: AccessTokens,
    private val refreshTokens: RefreshTokenRepository,
    private val apiKeys: ApiKeyRepository,
    private val refreshLifetime: Duration = Duration.ofDays(30),
    private val reuseGrace: Duration = Duration.ofSeconds(60),
) {
    suspend fun login(username: String, password: String, userAgent: String?): TokenPair {
        if (!passwords.verify(username, password)) throw Unauthorized("wrong username or password")
        return db.tx { session ->
            val user = users.byName(session, username.trim())!!
            pair(session, user.id, user.username, UUID.randomUUID(), userAgent)
        }
    }

    suspend fun refresh(token: String, userAgent: String?): TokenPair = db.tx { session ->
        val current = refreshTokens.byHashForUpdate(session, Secrets.hash(token)) ?: throw Unauthorized("unknown refresh token")
        when {
            current.revokedAt != null -> throw Unauthorized("refresh token revoked")
            // A retry of a rotation whose response never arrived (e.g. a laptop waking from sleep
            // on a half-up network): retire the successor the client never saw and issue a new one.
            current.usedAt != null && current.usedAt.plus(reuseGrace) > Instant.now() -> {
                log.info("Refresh token of family {} reused within the grace window; reissuing", current.familyId)
                refreshTokens.revokeUnusedSince(session, current.familyId, current.usedAt)
                val user = users.byId(session, current.userId) ?: throw Unauthorized("no such user")
                pair(session, user.id, user.username, current.familyId, userAgent ?: current.userAgent)
            }
            current.usedAt != null -> {
                log.warn("Refresh token of family {} used twice; revoking the family", current.familyId)
                refreshTokens.revokeFamily(session, current.familyId)
                null
            }
            current.expiresAt <= Instant.now() -> throw Unauthorized("refresh token expired")
            else -> {
                refreshTokens.markUsed(session, current.id)
                val user = users.byId(session, current.userId) ?: throw Unauthorized("no such user")
                pair(session, user.id, user.username, current.familyId, userAgent ?: current.userAgent)
            }
        }
    } ?: throw Unauthorized("refresh token already used; the session has been signed out")

    /** Signs out the session the refresh token belongs to. Unknown tokens are ignored. */
    suspend fun logout(token: String) = db.tx { session ->
        refreshTokens.byHashForUpdate(session, Secrets.hash(token))?.let { refreshTokens.revokeFamily(session, it.familyId) }
    }

    suspend fun sessions(userId: Long): List<RefreshToken> = db.io { refreshTokens.liveSessions(it, userId) }

    suspend fun endSession(userId: Long, familyId: UUID): Boolean = db.tx { refreshTokens.revokeFamily(it, userId, familyId) }

    /** Ends every session, e.g. after a password change. */
    suspend fun endAllSessions(userId: Long) = db.tx { refreshTokens.revokeAll(it, userId) }

    /** A new key; the returned secret is the only time it is visible. */
    suspend fun createApiKey(userId: Long, name: String): Pair<ApiKey, String> {
        val secret = API_KEY_PREFIX + Secrets.random(32)
        val key = db.tx { apiKeys.insert(it, userId, name.trim().ifEmpty { "API key" }, Secrets.hash(secret), secret.take(API_KEY_PREFIX.length + 6)) }
        return key to secret
    }

    suspend fun apiKeys(userId: Long): List<ApiKey> = db.io { apiKeys.live(it, userId) }

    suspend fun revokeApiKey(userId: Long, id: Long): Boolean = db.tx { apiKeys.revoke(it, userId, id) }

    /** Who a bearer credential belongs to: an API key by its prefix, anything else as an access token. */
    suspend fun authenticate(bearer: String): AuthInfo? {
        if (!bearer.startsWith(API_KEY_PREFIX)) return access.verify(bearer)
        return db.tx { session ->
            val key = apiKeys.byHash(session, Secrets.hash(bearer)) ?: return@tx null
            val user = users.byId(session, key.userId) ?: return@tx null
            apiKeys.touch(session, key.id)
            AuthInfo(user.id, user.username, AuthKind.API_KEY)
        }
    }

    private fun pair(session: kotliquery.Session, userId: Long, username: String, family: UUID, userAgent: String?): TokenPair {
        val refresh = Secrets.random(32)
        val refreshExpiresAt = Instant.now().plus(refreshLifetime).truncatedTo(ChronoUnit.SECONDS)
        refreshTokens.insert(session, userId, family, Secrets.hash(refresh), userAgent?.take(200), refreshExpiresAt)
        val (accessToken, accessExpiresAt) = access.issue(userId, username)
        return TokenPair(accessToken, accessExpiresAt, refresh, refreshExpiresAt)
    }

    companion object {
        /** Tells an API key from a JWT at a glance, here and in a leaked-secret scan. */
        const val API_KEY_PREFIX = "tt_"
    }
}
