package timetagger.routes

import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.server.request.header
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.delete
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.route
import timetagger.ApiException
import timetagger.NotFound
import timetagger.auth.AuthKind
import timetagger.auth.AuthService
import timetagger.auth.TokenPair
import timetagger.db.ApiKey
import timetagger.model.ApiKeyInfo
import timetagger.model.ApiKeyList
import timetagger.model.CreateApiKey
import timetagger.model.LoginRequest
import timetagger.model.Me
import timetagger.model.RefreshRequest
import timetagger.model.SessionInfo
import timetagger.model.SessionList
import timetagger.model.TokenPairResponse
import java.util.UUID

private fun TokenPair.response() = TokenPairResponse(accessToken, accessExpiresAt, refreshToken, refreshExpiresAt)

private fun ApiKey.info(secret: String? = null) = ApiKeyInfo(id, name, prefix, createdAt, lastUsedAt, secret)

/**
 * Unauthenticated: POST /auth/login {username, password} and POST /auth/refresh {refreshToken}
 * answer with a new access + refresh token pair; POST /auth/logout {refreshToken} ends that session.
 */
fun Route.authRoutes(auth: AuthService) = route("auth") {
    post("login") {
        val body = call.receive<LoginRequest>()
        call.respond(auth.login(body.username, body.password, call.request.header(HttpHeaders.UserAgent)).response())
    }
    post("refresh") {
        call.respond(auth.refresh(call.receive<RefreshRequest>().refreshToken, call.request.header(HttpHeaders.UserAgent)).response())
    }
    post("logout") {
        auth.logout(call.receive<RefreshRequest>().refreshToken)
        call.respond(HttpStatusCode.NoContent)
    }
}

/**
 * GET /me; GET /auth/sessions and DELETE /auth/sessions/{id} list and end signed-in devices;
 * GET, POST and DELETE /api-keys[/{id}] manage keys for scripts. Managing either needs an
 * access token: a leaked API key can't mint more keys or sign the owner out.
 */
fun Route.accountRoutes(auth: AuthService) {
    get("me") { call.respond(Me(call.auth.username)) }
    route("auth/sessions") {
        get {
            requireAccessToken()
            call.respond(SessionList(auth.sessions(call.auth.userId).map { SessionInfo(it.familyId.toString(), it.userAgent, it.lastRefreshedAt ?: it.createdAt, it.expiresAt) }))
        }
        delete("{id}") {
            requireAccessToken()
            val id = runCatching { UUID.fromString(call.path("id")) }.getOrNull() ?: throw NotFound("session")
            if (!auth.endSession(call.auth.userId, id)) throw NotFound("session")
            call.respond(HttpStatusCode.NoContent)
        }
    }
    route("api-keys") {
        get {
            requireAccessToken()
            call.respond(ApiKeyList(auth.apiKeys(call.auth.userId).map { it.info() }))
        }
        post {
            requireAccessToken()
            val (key, secret) = auth.createApiKey(call.auth.userId, call.receive<CreateApiKey>().name)
            call.respond(HttpStatusCode.Created, key.info(secret))
        }
        delete("{id}") {
            requireAccessToken()
            val id = call.path("id").toLongOrNull() ?: throw NotFound("API key")
            if (!auth.revokeApiKey(call.auth.userId, id)) throw NotFound("API key")
            call.respond(HttpStatusCode.NoContent)
        }
    }
}

private fun io.ktor.server.routing.RoutingContext.requireAccessToken() {
    if (call.auth.kind != AuthKind.ACCESS_TOKEN) {
        throw ApiException(HttpStatusCode.Forbidden, "forbidden", "sessions and API keys are managed with a signed-in session, not an API key")
    }
}
