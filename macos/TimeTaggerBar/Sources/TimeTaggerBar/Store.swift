import Foundation
import SwiftUI
import UserNotifications
import AppKit

enum Period: String, CaseIterable, Identifiable {
    case today = "Today", yesterday = "Yesterday", week = "This week", month = "This month"
    var id: String { rawValue }

    var range: (Int, Int) { range(in: .current) }

    /// The period's bounds as days in the given time zone ("today" in London starts at London midnight).
    func range(in timeZone: TimeZone) -> (Int, Int) {
        var cal = Calendar.current
        cal.timeZone = timeZone
        let now = Date()
        let start: Date
        var end: Date
        switch self {
        case .today:
            start = cal.startOfDay(for: now)
            end = cal.date(byAdding: .day, value: 1, to: start)!
        case .yesterday:
            end = cal.startOfDay(for: now)
            start = cal.date(byAdding: .day, value: -1, to: end)!
        case .week:
            start = cal.dateInterval(of: .weekOfYear, for: now)!.start
            end = cal.date(byAdding: .day, value: 7, to: start)!
        case .month:
            let iv = cal.dateInterval(of: .month, for: now)!
            start = iv.start
            end = iv.end
        }
        return (Int(start.timeIntervalSince1970), Int(end.timeIntervalSince1970))
    }
}

@MainActor
final class Store: ObservableObject {
    @AppStorage("serverURL") var serverURL = "https://timetagger.centralhardware.me"
    @AppStorage("workTimeZone") var workTimeZoneID = "Europe/London"
    @AppStorage("showWorkTime") var showWorkTime = true
    @AppStorage("pauseOnSleep") var pauseOnSleep = true
    @AppStorage("username") var username = ""
    /// Where a ticket tag like #sm-1061 opens; {key} becomes SM-1061. Empty turns the links off.
    @AppStorage("ticketURL") var ticketURL = ""
    @AppStorage("remindIdle") var remindIdle = true
    @AppStorage("workStartHour") var workStartHour = 9
    @AppStorage("workEndHour") var workEndHour = 18
    /// Signed in while the keychain holds a refresh token; the server signing us out clears it.
    @Published var signedIn = !Keychain.load().isEmpty
    let session = AuthSession()
    @Published var period: Period = .today
    @Published var records: [Record] = []
    @Published var running: [Record] = []
    @Published var error: String?
    @Published var lately: [Record] = []
    /// For autocomplete, most recently used first.
    @Published var tags: [String] = []
    @Published var serverVersion = "…"
    /// A newer release than this app, when GitHub has one.
    @Published var update: (version: String, url: URL)?
    /// The last change made from this app, until it is undone or goes stale.
    @Published var undoable: Change?
    private var lastNagged = 0

    struct Change {
        let label: String
        /// The records as they were, keyed by id; a record missing here was created by the change.
        let before: [String: Record]
        /// The records as the server saved them.
        let after: [Record]
        let at: Int
    }
    @Published var now = Int(Date().timeIntervalSince1970)

    private var tick: Timer?
    private var poll: Timer?
    /// The records that were running when the Mac went to sleep, and when it did.
    private var paused: [Record] = []
    private var sleptAt = 0

    init() {
        tick = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                self.now = Int(Date().timeIntervalSince1970)
                // Undo is offered for a while, not forever.
                if let u = self.undoable, self.now - u.at > 30 { self.undoable = nil }
                if self.now % 60 == 0 { self.nagIfIdle() }
            }
        }
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
        Task { await checkForUpdate() }
        // Changes arrive through watchChanges(); the poll only covers a stream that is down.
        poll = Timer.scheduledTimer(withTimeInterval: 300, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                Task { await self.refresh() }
            }
        }
        let ws = NSWorkspace.shared.notificationCenter
        ws.addObserver(forName: NSWorkspace.willSleepNotification, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { self?.willSleep() }
        }
        ws.addObserver(forName: NSWorkspace.didWakeNotification, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                Task { await self.didWake() }
            }
        }
        Task { await refresh() }
        Task { await watchChanges() }
    }

    /// Refreshes as soon as any client writes, reconnecting whenever the stream drops.
    private func watchChanges() async {
        while true {
            try? await api.watch { [weak self] in await self?.refresh() }
            try? await Task.sleep(nanoseconds: 5_000_000_000)
            // Catch up on whatever was written while the stream was down.
            await refresh()
        }
    }

    /// Closing the lid stops the running record at that moment; the network may
    /// already be gone, so didWake() repeats the stop before resuming.
    private func willSleep() {
        guard pauseOnSleep, !running.isEmpty else { return }
        paused = running
        sleptAt = Int(Date().timeIntervalSince1970)
        let stopped = stoppedCopies(paused, at: sleptAt)
        Task { try? await api.put(stopped) }
    }

    /// Opening the lid resumes what was paused as a new record.
    private func didWake() async {
        guard !paused.isEmpty else { return }
        let toResume = paused
        paused = []
        // Give Wi-Fi a moment to come back.
        try? await Task.sleep(nanoseconds: 5_000_000_000)
        let t = Int(Date().timeIntervalSince1970)
        let resumed = toResume.map { Record(key: Record.newKey(), rev: 0, t1: t, t2: t, ds: $0.ds, tags: $0.tags, deleted: 0) }
        await save(stoppedCopies(toResume, at: sleptAt) + resumed)
    }

    private func stoppedCopies(_ recs: [Record], at t: Int) -> [Record] {
        recs.map { var r = $0; r.t2 = max(t, r.t1 + 1); return r }
    }

    var api: API { API(baseURL: serverURL, session: session) }

    static var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "dev"
    }

    var workTimeZone: TimeZone { TimeZone(identifier: workTimeZoneID) ?? .current }

    /// Clock time of a timestamp in the local or the work time zone.
    func clock(_ t: Int, work: Bool = false) -> String {
        let f = DateFormatter()
        f.dateFormat = "HH:mm"
        f.timeZone = work ? workTimeZone : .current
        return f.string(from: Date(timeIntervalSince1970: TimeInterval(t)))
    }

    /// Short name of the work time zone's city ("Europe/London" → "London").
    var workZoneName: String {
        workTimeZoneID.split(separator: "/").last.map { $0.replacingOccurrences(of: "_", with: " ") } ?? workTimeZoneID
    }

    /// The second time zone is only worth showing when it differs from the Mac's.
    var showsWorkZone: Bool {
        showWorkTime && workTimeZone.secondsFromGMT() != TimeZone.current.secondsFromGMT()
    }

    /// Today's total, with "today" counted in the work time zone (it starts at work-zone midnight),
    /// so it matches the day the employer sees rather than the local calendar day.
    var todayTotal: Int {
        var cal = Calendar.current
        cal.timeZone = workTimeZone
        let start = Int(cal.startOfDay(for: Date()).timeIntervalSince1970)
        return lately.reduce(0) { $0 + max(0, ($1.isRunning ? now : $1.t2) - max($1.t1, start)) }
    }

    /// Menu bar text: today's total, preceded by the running timer when there is one.
    var menuTitle: String {
        let today = Self.format(todayTotal, seconds: false)
        guard let r = running.first else { return today }
        return Self.format(r.duration(now: now), seconds: false) + " · " + today
    }

    var totalsByTag: [(String, Int)] {
        var sums: [String: Int] = [:]
        let (p1, p2) = period.range
        for r in records {
            let t1 = max(r.t1, p1), t2 = min(r.isRunning ? now : r.t2, p2)
            guard t2 > t1 else { continue }
            let tags = r.tags.isEmpty ? ["untagged"] : r.tags
            for t in tags { sums[t, default: 0] += t2 - t1 }
        }
        return sums.sorted { $0.value > $1.value }
    }

    var total: Int {
        let (p1, p2) = period.range
        return records.reduce(0) { $0 + max(0, min($1.isRunning ? now : $1.t2, p2) - max($1.t1, p1)) }
    }

    func refresh() async {
        guard signedIn else { return }
        do {
            let (t1, t2) = period.range
            records = try await api.records(from: t1, to: t2)
                .filter { !$0.isDeleted }
                .sorted { $0.t1 > $1.t1 }
            // Running records and today's total come from the last 30 days.
            let n = Int(Date().timeIntervalSince1970)
            lately = try await api.records(from: n - 30 * 86400, to: n + 86400).filter { !$0.isDeleted }
            running = lately.filter(\.isRunning)
            // Autocomplete is a nicety: a server without the endpoint just offers none.
            tags = (try? await api.tags()) ?? tags
            serverVersion = (try? await api.version()) ?? "unreachable"
            error = nil
        } catch APIError.signedOut {
            signedOutLocally()
            self.error = APIError.signedOut.localizedDescription
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func save(_ recs: [Record], label: String? = nil, before: [Record] = []) async {
        do {
            let saved = try await api.put(recs)
            if let label {
                undoable = Change(label: label, before: Dictionary(before.map { ($0.key, $0) }) { a, _ in a },
                                  after: saved, at: Int(Date().timeIntervalSince1970))
            }
            await refresh()
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Puts back what the last change touched: edited records as they were, created ones deleted.
    func undo() async {
        guard let u = undoable else { return }
        undoable = nil
        let restore = u.after.map { saved -> Record in
            guard var old = u.before[saved.key] else { var r = saved; r.deleted = 1; return r }
            old.rev = saved.rev
            return old
        }
        await save(restore)
    }

    /// A notification when nothing is tracked during working hours on a weekday, at most every 30 minutes.
    private func nagIfIdle() {
        guard remindIdle, signedIn, running.isEmpty else { return }
        let cal = Calendar.current
        let date = Date(timeIntervalSince1970: TimeInterval(now))
        let hour = cal.component(.hour, from: date)
        guard !cal.isDateInWeekend(date), hour >= workStartHour, hour < workEndHour else { return }
        // Give a short break a chance, and don't repeat too often.
        let lastStop = lately.map(\.t2).max() ?? 0
        guard now - lastStop > 15 * 60, now - lastNagged > 30 * 60 else { return }
        lastNagged = now
        let content = UNMutableNotificationContent()
        content.title = "Not tracking"
        content.body = "Nothing has been running for \(Self.format(now - lastStop, seconds: false))."
        UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: "idle", content: content, trigger: nil))
    }

    /// The outcome of the last update check, for Settings → About.
    @Published var updateStatus = ""

    func checkForUpdate() async {
        updateStatus = "Checking…"
        do {
            guard let latest = try await API.latestRelease() else {
                update = nil
                updateStatus = "No releases found"
                return
            }
            update = latest.version.compare(Self.appVersion, options: .numeric) == .orderedDescending ? latest : nil
            updateStatus = update == nil ? "Up to date" : ""
        } catch {
            updateStatus = "Couldn't check: \(error.localizedDescription)"
        }
    }

    /// The link for a ticket tag such as "sm-1061", if a ticket URL is set and the tag looks like a key.
    func ticketLink(_ tag: String) -> URL? {
        guard !ticketURL.isEmpty, tag.range(of: #"^[a-z][a-z0-9]*-\d+$"#, options: .regularExpression) != nil else { return nil }
        return URL(string: ticketURL.replacingOccurrences(of: "{key}", with: tag.uppercased()))
    }

    /// Starts a new record, stopping whatever is running (like the web app's default).
    func start(_ description: String, tags: [String] = []) async {
        let t = Int(Date().timeIntervalSince1970)
        let stopped = running.map { r -> Record in var r = r; r.t2 = max(t, r.t1 + 1); return r }
        let new = Record(key: Record.newKey(), rev: 0, t1: t, t2: t, ds: description.trimmingCharacters(in: .whitespaces), tags: tags, deleted: 0)
        await save(stopped + [new], label: "Started \u{201C}\(new.ds)\u{201D}", before: running)
    }

    func stop(_ record: Record? = nil) async {
        let t = Int(Date().timeIntervalSince1970)
        let targets = record.map { [$0] } ?? running
        await save(targets.map { var r = $0; r.t2 = max(t, r.t1 + 1); return r }, label: "Stopped", before: targets)
    }

    func update(_ record: Record) async {
        await save([record], label: "Edited", before: (lately + records).filter { $0.key == record.key })
    }

    func delete(_ record: Record) async {
        var r = record
        r.deleted = 1
        await save([r], label: "Deleted \u{201C}\(record.ds)\u{201D}", before: [record])
    }

    func signIn(url: String, username: String, password: String) async throws {
        try await API(baseURL: url, session: session).login(username: username, password: password)
        serverURL = url
        self.username = username
        signedIn = true
        await refresh()
    }

    func signOut() async {
        await api.logout()
        signedOutLocally()
    }

    /// What's left to do once the session is gone, by choice or because the server ended it.
    private func signedOutLocally() {
        signedIn = false
        username = ""
        running = []
        records = []
        lately = []
    }

    nonisolated static func format(_ secs: Int, seconds: Bool = true) -> String {
        let h = secs / 3600, m = (secs % 3600) / 60, s = secs % 60
        return seconds ? String(format: "%d:%02d:%02d", h, m, s) : String(format: "%d:%02d", h, m)
    }
}
