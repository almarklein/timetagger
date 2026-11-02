package timetagger

import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.request
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpMethod
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.server.cio.CIO
import io.ktor.server.engine.embeddedServer
import io.ktor.server.testing.ApplicationTestBuilder
import io.ktor.server.testing.testApplication
import io.zonky.test.db.postgres.embedded.EmbeddedPostgres
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import org.flywaydb.core.Flyway
import timetagger.auth.PasswordService
import timetagger.config.Config
import timetagger.db.Database
import timetagger.db.RecordRepository
import timetagger.db.SettingRepository
import timetagger.db.UserRepository
import timetagger.model.RecordInput
import timetagger.service.RecordService
import timetagger.service.SyncService
import ch.qos.logback.classic.Logger
import ch.qos.logback.classic.spi.ILoggingEvent
import ch.qos.logback.core.read.ListAppender
import org.slf4j.LoggerFactory
import java.time.Instant
import java.net.URI
import java.net.http.HttpRequest
import java.net.http.HttpResponse.BodyHandlers
import java.util.Base64
import kotlin.test.AfterTest
import kotlin.test.BeforeTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

private const val API = "/timetagger/api/v1"

class ApiTest {
    private lateinit var pg: EmbeddedPostgres
    private lateinit var db: Database

    @BeforeTest
    fun setUp() {
        pg = EmbeddedPostgres.start()
        db = Database("postgresql://postgres:postgres@localhost:${pg.port}/postgres")
        db.migrate()
        runBlocking { PasswordService(db, UserRepository()).set("alice", "secret") }
    }

    @AfterTest
    fun tearDown() {
        db.close()
        pg.close()
    }

    private fun api(block: suspend ApplicationTestBuilder.() -> Unit) = testApplication {
        application { module(Config(jwtKey = "test-key", autoMerge = false), db) }
        block()
    }

    private suspend fun ApplicationTestBuilder.login(user: String = "alice", pw: String = "secret") =
        client.post("$API/auth/login") { contentType(ContentType.Application.Json); setBody("""{"username":"$user","password":"$pw"}""") }

    private suspend fun ApplicationTestBuilder.refresh(token: String) =
        client.post("$API/auth/refresh") { contentType(ContentType.Application.Json); setBody("""{"refreshToken":"$token"}""") }

    private suspend fun ApplicationTestBuilder.token() = login().obj()["accessToken"]!!.jsonPrimitive.content

    private suspend fun ApplicationTestBuilder.me(bearer: String) = client.get("$API/me") { header("Authorization", "Bearer $bearer") }

    private suspend fun HttpResponse.obj(): JsonObject = Json.parseToJsonElement(bodyAsText()).jsonObject

    @Test
    fun loginRefreshAndLogout() = api {
        assertEquals(HttpStatusCode.Unauthorized, login(pw = "wrong").status)
        val first = login().obj()
        val access = first["accessToken"]!!.jsonPrimitive.content
        val refreshToken = first["refreshToken"]!!.jsonPrimitive.content
        assertEquals("alice", me(access).obj()["username"]!!.jsonPrimitive.content)

        // A refresh rotates: the new pair works, the old refresh token is spent.
        val second = refresh(refreshToken).obj()
        val refreshed = second["refreshToken"]!!.jsonPrimitive.content
        assertEquals(HttpStatusCode.OK, me(second["accessToken"]!!.jsonPrimitive.content).status)
        // Presenting the spent one again right away is a retry whose response was lost (a Mac
        // waking from sleep): it gets a fresh pair, and the successor it never saw dies.
        val retried = refresh(refreshToken)
        assertEquals(HttpStatusCode.OK, retried.status)
        val third = retried.obj()["refreshToken"]!!.jsonPrimitive.content
        assertEquals(HttpStatusCode.Unauthorized, refresh(refreshed).status)

        // Outside the grace window a second use looks like theft: the whole session ends.
        db.tx { it.execute(kotliquery.queryOf("UPDATE refresh_tokens SET used_at = now() - interval '5 minutes' WHERE used_at IS NOT NULL")) }
        assertEquals(HttpStatusCode.Unauthorized, refresh(refreshToken).status)
        assertEquals(HttpStatusCode.Unauthorized, refresh(third).status)

        // Logout ends a session for good.
        val other = login().obj()["refreshToken"]!!.jsonPrimitive.content
        client.post("$API/auth/logout") { contentType(ContentType.Application.Json); setBody("""{"refreshToken":"$other"}""") }
        assertEquals(HttpStatusCode.Unauthorized, refresh(other).status)

        val bad = me("not-a-token")
        assertEquals(HttpStatusCode.Unauthorized, bad.status)
        assertEquals("unauthorized", bad.obj()["error"]!!.jsonPrimitive.content)
        assertEquals(HttpStatusCode.Unauthorized, client.get("$API/me").status)
    }

    @Test
    fun sessionsAndApiKeys() = api {
        val access = token()
        val sessions = client.get("$API/auth/sessions") { header("Authorization", "Bearer $access") }.obj()["sessions"]!!.jsonArray
        assertEquals(1, sessions.size)

        val created = client.post("$API/api-keys") {
            header("Authorization", "Bearer $access"); contentType(ContentType.Application.Json); setBody("""{"name":"merge cron"}""")
        }.obj()
        val key = created["key"]!!.jsonPrimitive.content
        assertTrue(key.startsWith("tt_"))
        assertEquals("alice", me(key).obj()["username"]!!.jsonPrimitive.content)
        // The key is shown once: the list has its name and prefix only.
        val listed = client.get("$API/api-keys") { header("Authorization", "Bearer $access") }.obj()["apiKeys"]!!.jsonArray.single().jsonObject
        assertEquals("merge cron", listed["name"]!!.jsonPrimitive.content)
        assertNull(listed["key"]?.takeIf { it !is kotlinx.serialization.json.JsonNull })
        assertTrue(key.startsWith(listed["prefix"]!!.jsonPrimitive.content))
        // A key can't manage keys or sessions.
        assertEquals(HttpStatusCode.Forbidden, client.post("$API/api-keys") { header("Authorization", "Bearer $key"); contentType(ContentType.Application.Json); setBody("{}") }.status)
        assertEquals(HttpStatusCode.Forbidden, client.get("$API/auth/sessions") { header("Authorization", "Bearer $key") }.status)
        // Revoking one key ends it alone.
        val id = created["id"]!!.jsonPrimitive.long
        assertEquals(HttpStatusCode.NoContent, client.delete("$API/api-keys/$id") { header("Authorization", "Bearer $access") }.status)
        assertEquals(HttpStatusCode.Unauthorized, me(key).status)
        assertEquals(HttpStatusCode.OK, me(access).status)

        // Ending a session stops its refresh token.
        val fresh = login().obj()["refreshToken"]!!.jsonPrimitive.content
        val all = client.get("$API/auth/sessions") { header("Authorization", "Bearer $access") }.obj()["sessions"]!!.jsonArray
        all.forEach { client.delete("$API/auth/sessions/${it.jsonObject["id"]!!.jsonPrimitive.content}") { header("Authorization", "Bearer $access") } }
        assertEquals(HttpStatusCode.Unauthorized, refresh(fresh).status)
    }

    @Test
    fun newPasswordEndsSessions() = api {
        val refreshToken = login().obj()["refreshToken"]!!.jsonPrimitive.content
        PasswordService(db, UserRepository()).set("alice", "changed")
        assertEquals(HttpStatusCode.Unauthorized, refresh(refreshToken).status)
        assertEquals(HttpStatusCode.OK, login(pw = "changed").status)
    }

    @Test
    fun publicEndpoints() = api {
        val web = token()
        assertEquals(HttpStatusCode.OK, client.get("$API/version").status)
        assertEquals("ok", client.get("/timetagger/status").bodyAsText())
        // The bare domain works as the base URL too.
        assertEquals("ok", client.get("/status").bodyAsText())
        assertEquals("alice", client.get("/api/v1/me") { header("Authorization", "Bearer $web") }.obj()["username"]!!.jsonPrimitive.content)
        assertEquals("not_found", client.get("$API/nope") { header("Authorization", "Bearer $web") }.obj()["error"]!!.jsonPrimitive.content)
    }

    @Test
    fun records() = api {
        val t = token()
        suspend fun send(method: String, path: String, body: String) = client.request("$API/$path") {
            this.method = HttpMethod.parse(method)
            header("Authorization", "Bearer $t"); contentType(ContentType.Application.Json); setBody(body)
        }
        suspend fun create(body: String): Long {
            val r = send("POST", "records", body)
            assertEquals(HttpStatusCode.Created, r.status, r.bodyAsText())
            return r.obj()["id"]!!.jsonPrimitive.long.also { assertEquals("$API/records/$it", r.headers["Location"]) }
        }
        suspend fun list(q: String) = client.get("$API/records?$q") { header("Authorization", "Bearer $t") }
            .obj()["records"]!!.jsonArray.map { it.jsonObject["id"]!!.jsonPrimitive.long }

        val a = create("""{"start":"2026-10-28T08:00:00Z","stop":"2026-10-28T09:00:00Z","description":"code","tags":["#Work"]}""")
        assertEquals(listOf("work"), client.get("$API/records/$a") { header("Authorization", "Bearer $t") }.obj()["tags"]!!.jsonArray.map { it.jsonPrimitive.content })
        val b = create("""{"start":"2026-10-28T10:00:00Z","description":"run #literal","tags":["work","x"]}""")
        // A # in the description is just text.
        assertEquals(listOf("work", "x"), client.get("$API/records/$b") { header("Authorization", "Bearer $t") }.obj()["tags"]!!.jsonArray.map { it.jsonPrimitive.content })
        assertEquals(HttpStatusCode.UnprocessableEntity, send("POST", "records", """{"start":"2026-10-28T10:00:00Z","tags":["two words"]}""").status)
        assertEquals(b, a + 1)
        assertEquals(HttpStatusCode.UnprocessableEntity, send("POST", "records", """{"start":"2026-10-28T10:00:00Z","stop":"2026-10-28T09:00:00Z"}""").status)
        assertEquals(HttpStatusCode.UnprocessableEntity, send("POST", "records", """{"stop":"nope"}""").status)
        assertEquals(HttpStatusCode.NotFound, send("PUT", "records/999", """{"start":"2026-10-28T10:00:00Z"}""").status)
        assertEquals(HttpStatusCode.NotFound, client.get("$API/records/abc") { header("Authorization", "Bearer $t") }.status)

        val day = "from=2026-10-28T00:00:00Z&to=2026-10-29T00:00:00Z"
        assertEquals(listOf(a, b), list(day))
        assertEquals(listOf(b), list("$day&running=true"))
        assertEquals(listOf(b), list("$day&tag=x&tag=work"))
        // Tags in use, the latest first; b started after a.
        assertEquals(listOf("work", "x"), client.get("$API/records/tags") { header("Authorization", "Bearer $t") }.obj()["tags"]!!.jsonArray.map { it.jsonPrimitive.content })
        // Search needs no range and matches any part of the description or a tag, case aside; % is literal.
        assertEquals(listOf(a), list("q=CODE"))
        assertEquals(listOf(a, b), list("q=WOR"))
        assertEquals(emptyList(), list("q=%25"))
        // A running record overlaps any later range.
        assertEquals(listOf(b), list("from=2026-11-01T00:00:00Z&to=2026-11-02T00:00:00Z"))
        assertEquals(HttpStatusCode.UnprocessableEntity, client.get("$API/records?from=yesterday&to=now") { header("Authorization", "Bearer $t") }.status)

        // An edit based on an old revision is refused with the current record; the current revision goes through.
        val aRev = client.get("$API/records/$a") { header("Authorization", "Bearer $t") }.obj()["revision"]!!.jsonPrimitive.long
        val stale = send("PUT", "records/$a", """{"start":"2026-10-28T08:00:00Z","description":"old","revision":${aRev - 1}}""")
        assertEquals(HttpStatusCode.Conflict, stale.status)
        assertEquals("code", stale.obj()["current"]!!.jsonObject["description"]!!.jsonPrimitive.content)
        assertEquals(HttpStatusCode.OK, send("PUT", "records/$a", """{"start":"2026-10-28T08:00:00Z","stop":"2026-10-28T09:00:00Z","description":"code","tags":["work"],"revision":$aRev}""").status)

        // Stop b and start a new one in one go; one bad entry rejects the whole batch.
        val batch = send("POST", "records/batch", """{"records":[{"id":$b,"start":"2026-10-28T10:00:00Z","stop":"2026-10-28T11:00:00Z","description":"run","tags":["work"]},
            {"start":"2026-10-28T11:00:00Z","description":"next"}]}""").obj()["records"]!!.jsonArray
        val c = batch[1].jsonObject["id"]!!.jsonPrimitive.long
        val badBatch = send("POST", "records/batch", """{"records":[{"start":"2026-10-28T12:00:00Z","description":"lost"},{"id":999,"start":"2026-10-28T12:00:00Z"}]}""")
        assertEquals(HttpStatusCode.NotFound, badBatch.status)
        assertEquals(listOf(a, b, c), list(day))
        assertEquals(listOf(c), list("$day&running=true"))

        assertEquals(HttpStatusCode.NoContent, client.delete("$API/records/$a") { header("Authorization", "Bearer $t") }.status)
        assertEquals(listOf(b, c), list(day))
        assertEquals(listOf(a), list("$day&deleted=true"))
        assertEquals(HttpStatusCode.NotFound, client.delete("$API/records/12345") { header("Authorization", "Bearer $t") }.status)

        // Sync: everything after a revision, deletes included.
        val all = client.get("$API/changes") { header("Authorization", "Bearer $t") }.obj()
        val rev = all["revision"]!!.jsonPrimitive.long
        assertEquals(3, all["records"]!!.jsonArray.size)
        send("PUT", "records/$c", """{"start":"2026-10-28T11:00:00Z","stop":"2026-10-28T11:30:00Z","description":"next"}""")
        val after = client.get("$API/changes?since=$rev") { header("Authorization", "Bearer $t") }.obj()
        assertEquals(listOf(c), after["records"]!!.jsonArray.map { it.jsonObject["id"]!!.jsonPrimitive.long })
    }

    /** Over a real server: the test engine holds a streamed response back until it ends. */
    @Test
    fun changeStream() {
        val server = embeddedServer(CIO, port = 0) { module(Config(jwtKey = "test-key", autoMerge = false), db) }.start()
        try {
            val base = runBlocking { "http://localhost:${server.engine.resolvedConnectors().first().port}$API" }
            val http = java.net.http.HttpClient.newHttpClient()
            fun call(method: String, path: String, auth: String, body: String = "") = http.send(
                HttpRequest.newBuilder(URI("$base/$path")).header("Authorization", auth).header("Content-Type", "application/json")
                    .method(method, HttpRequest.BodyPublishers.ofString(body)).build(),
                BodyHandlers.ofString(),
            ).body()
            val t = Json.parseToJsonElement(call("POST", "auth/login", "", """{"username":"alice","password":"secret"}""")).jsonObject["accessToken"]!!.jsonPrimitive.content
            val lines = http.send(
                HttpRequest.newBuilder(URI("$base/changes/stream")).header("Authorization", "Bearer $t").build(),
                BodyHandlers.ofLines(),
            ).body().iterator()
            call("POST", "records", "Bearer $t", """{"start":"2026-10-28T08:00:00Z"}""")
            assertEquals("event: change", lines.asSequence().first { it.startsWith("event:") })
        } finally {
            server.stop(0, 0)
        }
    }

    /** A write that commits late still lands above every revision a client could already have synced. */
    @Test
    fun writesCommitInRevisionOrder() = runBlocking {
        val repo = RecordRepository()
        val records = RecordService(db, repo)
        val alice = db.io { UserRepository().byName(it, "alice") }!!.id
        val start = Instant.parse("2026-10-28T08:00:00Z")
        coroutineScope {
            // Slow takes the lock first and holds it a while before writing.
            val slow = async { db.write(alice) { s -> Thread.sleep(500); repo.create(s, alice, start, null, "slow", emptyList(), null) } }
            delay(100)
            val fast = async { records.create(alice, RecordInput(start = start, description = "fast")) }
            val (a, b) = slow.await() to fast.await()
            assertTrue(b.revision > a.revision, "fast (${b.revision}) must come after slow (${a.revision})")
        }
    }

    @Test
    fun syncSnapshotCoversWhatItReturns() = runBlocking {
        val sync = SyncService(db, RecordRepository(), SettingRepository())
        val records = RecordService(db, RecordRepository())
        val alice = db.io { UserRepository().byName(it, "alice") }!!.id
        val start = Instant.parse("2026-10-28T08:00:00Z")
        val seen = mutableSetOf<Long>()
        var since = 0L
        val written = coroutineScope {
            val writers = (1..20).map { i -> async { records.create(alice, RecordInput(start = start, description = "w$i")).id } }
            // Sync alongside the writers, the way a client would.
            while (writers.any { it.isActive }) {
                val c = sync.changes(alice, since)
                c.records.forEach { seen += it.id }
                since = c.revision
            }
            writers.map { it.await() }
        }
        sync.changes(alice, since).records.forEach { seen += it.id }
        assertEquals(written.toSet(), seen)
    }

    @Test
    fun requestsAreLogged() = api {
        val appender = ListAppender<ILoggingEvent>().apply { start() }
        val logger = LoggerFactory.getLogger("timetagger.http") as Logger
        logger.addAppender(appender)
        try {
            val t = token()
            client.get("$API/records?from=2026-10-28T00:00:00Z&to=2026-10-29T00:00:00Z") { header("Authorization", "Bearer $t") }
            client.get("/timetagger/status")
            val lines = appender.list.map { it.formattedMessage }
            assertTrue(lines.any { it.startsWith("GET /timetagger/api/v1/records 200 alice ") && it.endsWith("ms") }, lines.toString())
            assertTrue(lines.none { "/status" in it }, lines.toString())
        } finally {
            logger.detachAppender(appender)
        }
    }

    @Test
    fun startingARecordStopsTheRunningOne() = api {
        val t = token()
        suspend fun create(body: String) = client.post("$API/records") {
            header("Authorization", "Bearer $t"); contentType(ContentType.Application.Json); setBody(body)
        }.obj()
        val first = create("""{"start":"2026-10-28T08:00:00Z","description":"first"}""")["id"]!!.jsonPrimitive.long
        create("""{"start":"2026-10-28T09:00:00Z","description":"second"}""")
        val stopped = client.get("$API/records/$first") { header("Authorization", "Bearer $t") }.obj()
        assertEquals("2026-10-28T09:00:00Z", stopped["stop"]!!.jsonPrimitive.content)
        // A closed record doesn't stop anything.
        create("""{"start":"2026-10-28T07:00:00Z","stop":"2026-10-28T07:30:00Z","description":"earlier"}""")
        val running = client.get("$API/records?from=2026-10-28T00:00:00Z&to=2026-10-29T00:00:00Z&running=true") { header("Authorization", "Bearer $t") }
            .obj()["records"]!!.jsonArray.map { it.jsonObject["description"]!!.jsonPrimitive.content }
        assertEquals(listOf("second"), running)
    }

    @Test
    fun settings() = api {
        val t = token()
        val r = client.put("$API/settings/workdays") {
            header("Authorization", "Bearer $t"); contentType(ContentType.Application.Json); setBody("""{"value":2}""")
        }
        assertEquals(HttpStatusCode.OK, r.status)
        val s = client.get("$API/settings") { header("Authorization", "Bearer $t") }.obj()["settings"]!!.jsonArray
        assertEquals("2", s.single().jsonObject["value"]!!.jsonPrimitive.content)
        // A write based on a stale revision leaves the stored value.
        val rev = s.single().jsonObject["revision"]!!.jsonPrimitive.long
        val stale = client.put("$API/settings/workdays") {
            header("Authorization", "Bearer $t"); contentType(ContentType.Application.Json); setBody("""{"value":5,"revision":${rev - 1}}""")
        }
        assertEquals("2", stale.obj()["value"]!!.jsonPrimitive.content)
        assertEquals(HttpStatusCode.NotFound, client.get("$API/settings/none") { header("Authorization", "Bearer $t") }.status)
    }
}

/** V5 converts a database written by the v2 server. */
class V5MigrationTest {
    @Test
    fun convertsV2Data() {
        EmbeddedPostgres.start().use { pg ->
            val flyway = Flyway.configure().dataSource(pg.postgresDatabase).locations("classpath:db/migration")
            flyway.target("4").load().migrate()
            pg.postgresDatabase.connection.use { c ->
                c.createStatement().use { st ->
                    st.execute("INSERT INTO credentials (username, pw_hash) VALUES ('alex', 'hash')")
                    st.execute(
                        """
                        INSERT INTO records ("user", "key", modified_time, start_time, stop_time, description, deleted, server_time) VALUES
                          ('alex', 'done', 100, 1000, 2000, '#Work code #call', 0, 5.5),
                          ('alex', 'run', 101, 3000, 3000, 'running', 0, 6.5),
                          ('alex', 'gone', 102, 500, 600, 'x', 1, 4.5)
                        """,
                    )
                    st.execute("""INSERT INTO settings ("user", "key", modified_time, value, server_time) VALUES ('alex', 'workdays', 1, '2', 1)""")
                    st.execute("""INSERT INTO userinfo ("user", "key", modified_time, value, server_time) VALUES ('alex', 'apitoken_seed', 1, '"seed1"', 1)""")
                }
            }
            flyway.target("latest").load().migrate()
            pg.postgresDatabase.connection.use { c ->
                c.createStatement().use { st ->
                    fun one(sql: String) = st.executeQuery(sql).let { it.next(); it.getString(1) }
                    assertEquals("hash", one("SELECT password_hash FROM users WHERE username = 'alex'"))
                    // V7 drops the seeds: tokens from before the refresh-token scheme are void.
                    assertEquals("0", one("SELECT count(*) FROM information_schema.columns WHERE column_name = 'api_token_seed'"))
                    assertNull(one("SELECT stop_at FROM records WHERE description = 'running'"))
                    assertEquals("1", one("SELECT count(*) FROM records WHERE deleted_at IS NOT NULL"))
                    assertEquals("call,work", one("SELECT string_agg(tag, ',' ORDER BY tag) FROM record_tags"))
                    // Revisions follow the old server-time order; V8 then moves the #tags out of the text, bumping that record.
                    assertEquals("x,running,code", one("SELECT string_agg(description, ',' ORDER BY revision) FROM records"))
                    assertEquals("1,2,3", one("SELECT string_agg(id::text, ',' ORDER BY id) FROM records"))
                    assertEquals("2", one("SELECT value::text FROM settings"))
                    assertEquals("0", one("SELECT count(*) FROM pg_tables WHERE tablename IN ('credentials', 'userinfo', 'schema_migrations')"))
                }
            }
        }
    }
}
