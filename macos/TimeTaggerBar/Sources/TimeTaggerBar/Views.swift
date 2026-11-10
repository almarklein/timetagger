import ServiceManagement
import SwiftUI

struct MenuView: View {
    @EnvironmentObject var store: Store
    @Environment(\.openWindow) private var openWindow
    @State private var draft = ""
    @State private var draftTags = ""
    @State private var editing: Record?
    @StateObject private var feed = DayFeed()

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let err = store.error {
                Text(err).font(.caption).foregroundStyle(.red).lineLimit(3)
            }
            if let u = store.undoable {
                HStack {
                    Text(u.label).lineLimit(1).foregroundStyle(.secondary)
                    Spacer()
                    Button("Undo") { Task { await store.undo() } }
                        .keyboardShortcut("z", modifiers: .command)
                }
                .font(.callout)
            }
            if let u = store.update {
                Link("TimeTaggerBar \(u.version) is available", destination: u.url).font(.callout)
            }

            if let r = store.running.first {
                runningCard(r)
                taskField("Switch to…", icon: "play")
            } else {
                idleCard
            }

            daySection

            Divider()

            HStack(spacing: 10) {
                Text("Today").foregroundStyle(.secondary)
                Text(Store.format(store.todayTotal, seconds: false)).bold().monospacedDigit()
                Spacer()
                Button("History") {
                    openWindow(id: "history")
                    NSApp.activate(ignoringOtherApps: true)
                }
                .keyboardShortcut("y", modifiers: .command)
                Button("Report") {
                    openWindow(id: "report")
                    NSApp.activate(ignoringOtherApps: true)
                }
                .keyboardShortcut("r", modifiers: [.command, .shift])
                Menu {
                    Button("Settings…") {
                        openWindow(id: "settings")
                        NSApp.activate(ignoringOtherApps: true)
                    }
                    .keyboardShortcut(",", modifiers: .command)
                    Button("Refresh") { Task { await store.refresh() } }
                        .keyboardShortcut("r", modifiers: .command)
                    Divider()
                    Button("Quit TimeTaggerBar") { NSApp.terminate(nil) }
                        .keyboardShortcut("q", modifiers: .command)
                } label: { Image(systemName: "ellipsis.circle") }
                    .menuStyle(.borderlessButton)
                    .fixedSize()
                    .accessibilityLabel("More")
            }
            .buttonStyle(.link)
            .font(.callout)
        }
        .padding(16)
        .frame(width: 340)
        .sheet(item: $editing) { r in
            EditRecordView(record: r).environmentObject(store)
        }
        // Reload whenever the store has refreshed (a write here or anywhere else).
        .task(id: store.lately.hashValue) { await load { try await feed.reload(store.api) } }
    }

    /// Today first, older days below, loading further back as the end scrolls into view.
    private var daySection: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0, pinnedViews: .sectionHeaders) {
                ForEach(feed.days()) { day in
                    Section {
                        ForEach(day.records) { r in dayRow(r) }
                    } header: {
                        HStack {
                            Text(Calendar.current.isDateInToday(day.id) ? "Today" : day.id.formatted(.dateTime.weekday(.abbreviated).day().month(.abbreviated)))
                                .font(.caption.weight(.semibold))
                            Spacer()
                            Text(Store.format(day.records.reduce(0) { $0 + $1.duration(now: store.now) }, seconds: false))
                                .font(.caption).monospacedDigit()
                        }
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 6).padding(.vertical, 4)
                        .background(.regularMaterial)
                    }
                }
                if !feed.reachedEnd {
                    ProgressView().controlSize(.small).frame(maxWidth: .infinity).padding(8)
                        .onAppear { Task { await load { try await feed.loadMore(store.api) } } }
                }
            }
        }
        .frame(height: 300)
    }

    private func dayRow(_ r: Record) -> some View {
        HStack(spacing: 8) {
            Text(store.clock(r.t1) + "–" + (r.isRunning ? "now" : store.clock(r.t2)))
                .font(.caption).monospacedDigit().foregroundStyle(.secondary)
                .frame(width: 82, alignment: .leading)
            Text(r.ds.isEmpty ? "(no description)" : r.ds).lineLimit(1)
            TagLine(tags: r.tags)
            Spacer()
            Text(Store.format(r.duration(now: store.now), seconds: false)).monospacedDigit().foregroundStyle(.secondary)
            if !r.isRunning {
                Button { Task { await store.start(r.ds, tags: r.tags) } } label: { Image(systemName: "play.fill") }
                    .buttonStyle(.borderless)
                    .help("Resume")
                    .accessibilityLabel("Resume \(r.ds)")
            }
        }
        .font(.callout)
        .padding(.horizontal, 6)
        .frame(height: 26)
        .contentShape(Rectangle())
        .onTapGesture { editing = r }
        .help("Click to edit")
        .contextMenu {
            Button("Edit…") { editing = r }
            Button("Resume") { Task { await store.start(r.ds, tags: r.tags) } }
            if r.isRunning { Button("Stop") { Task { await store.stop(r) } } }
            TicketLinks(record: r)
            Divider()
            Button("Delete", role: .destructive) { Task { await store.delete(r) } }
        }
    }

    private func runningCard(_ r: Record) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Tracking", systemImage: "circle.fill")
                .font(.caption.weight(.semibold)).textCase(.uppercase)
                .foregroundStyle(.red)
            HStack(spacing: 14) {
                Text("Since **\(store.clock(r.t1))** local")
                if store.showsWorkZone {
                    Text("**\(store.clock(r.t1, work: true))** \(store.workZoneName) · work")
                }
            }
            .font(.callout).foregroundStyle(.secondary).monospacedDigit()
            Text(Store.format(r.duration(now: store.now)))
                .font(.system(.largeTitle, design: .rounded).weight(.light)).monospacedDigit()
            Text(r.ds.isEmpty ? "(no description)" : r.ds).font(.headline).lineLimit(2)
            TagLine(tags: r.tags).font(.callout)
            HStack(spacing: 8) {
                Button { Task { await store.stop(r) } } label: {
                    Label("Stop", systemImage: "stop.fill").frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent).tint(.red)
                .keyboardShortcut(".", modifiers: .command)
                .help("Stop (⌘.)")
                Button { editing = r } label: { Image(systemName: "pencil") }
                    .keyboardShortcut("e", modifiers: .command)
                    .help("Edit current record (⌘E)")
                    .accessibilityLabel("Edit current record")
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    private var idleCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Not tracking").font(.caption.weight(.semibold)).textCase(.uppercase).foregroundStyle(.secondary)
                Spacer()
                Text("**\(store.clock(store.now))** local")
                if store.showsWorkZone { Text("**\(store.clock(store.now, work: true))** \(store.workZoneName)") }
            }
            .font(.callout).monospacedDigit()
            taskField("What are you working on?", icon: nil)
            Button(action: startDraft) {
                Label("Start", systemImage: "play.fill").frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty && draftTags.isEmpty)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    private func taskField(_ prompt: String, icon: String?) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                if let icon { Image(systemName: icon).foregroundStyle(.secondary) }
                TextField(prompt, text: $draft)
                    .textFieldStyle(.plain)
                    .onSubmit(startDraft)
                Divider().frame(height: 18)
                Image(systemName: "number").foregroundStyle(.secondary)
                TextField("tags", text: $draftTags)
                    .textFieldStyle(.plain)
                    .frame(width: 110)
                    .onSubmit(startDraft)
            }
            .padding(.horizontal, 8)
            .frame(height: 28)
            .background(.quaternary.opacity(0.6), in: RoundedRectangle(cornerRadius: 6, style: .continuous))
            TagSuggestions(text: $draftTags, tags: store.tags)
        }
    }

    private func startDraft() {
        let ds = draft
        let tags = Record.parseTags(draftTags)
        draft = ""
        draftTags = ""
        Task { await store.start(ds, tags: tags) }
    }

    private func load(_ op: () async throws -> Void) async {
        do { try await op() } catch { store.error = error.localizedDescription }
    }
}

/// Signed-in devices and API keys for scripts, each revocable on its own.
struct AccessSection: View {
    @EnvironmentObject var store: Store
    @State private var sessions: [API.SignedInSession] = []
    @State private var keys: [API.ApiKey] = []
    @State private var newKeyName = ""
    /// A just-created key, shown until the window closes: the server never shows it again.
    @State private var created: API.ApiKey?
    @State private var problem = ""

    var body: some View {
        Section("Signed-in devices") {
            ForEach(sessions) { s in
                LabeledContent(s.userAgent ?? "Unknown device") {
                    HStack {
                        Text(s.lastRefreshedAt, format: .relative(presentation: .named)).foregroundStyle(.secondary)
                        Button("Sign Out") { run { try await store.api.endSession(s.id) } }
                    }
                }
            }
        }
        Section("API keys") {
            ForEach(keys) { k in
                LabeledContent(k.name) {
                    HStack {
                        Text("\(k.prefix)…").font(.caption.monospaced()).foregroundStyle(.secondary)
                        Button("Revoke") { run { try await store.api.revokeApiKey(k.id) } }
                    }
                }
            }
            if let key = created?.key {
                HStack {
                    Text(key).font(.caption.monospaced()).textSelection(.enabled).lineLimit(1).truncationMode(.middle)
                    Button("Copy") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(key, forType: .string)
                    }
                }
                Text("Copy it now: it won't be shown again.").font(.caption).foregroundStyle(.secondary)
            }
            HStack {
                TextField("New key name", text: $newKeyName, prompt: Text("e.g. merge cron"))
                Button("Create") {
                    let name = newKeyName
                    run {
                        created = try await store.api.createApiKey(name: name)
                        newKeyName = ""
                    }
                }
            }
            if !problem.isEmpty { Text(problem).font(.caption).foregroundStyle(.red) }
        }
        .task { await load() }
    }

    private func run(_ op: @escaping () async throws -> Void) {
        Task {
            do { try await op(); problem = "" } catch { problem = error.localizedDescription }
            await load()
        }
    }

    private func load() async {
        do {
            sessions = try await store.api.sessions()
            keys = try await store.api.apiKeys()
        } catch {
            problem = error.localizedDescription
        }
    }
}

/// "Open SM-1061" for every ticket tag on the record, when a ticket URL is set.
struct TicketLinks: View {
    @EnvironmentObject var store: Store
    let record: Record

    var body: some View {
        ForEach(record.tags.compactMap { t in store.ticketLink(t).map { (t, $0) } }, id: \.0) { tag, url in
            Link("Open \(tag.uppercased())", destination: url)
        }
    }
}

/// The record's tags as quiet "#a #b" text.
struct TagLine: View {
    let tags: [String]

    var body: some View {
        if !tags.isEmpty {
            Text(tags.map { "#" + $0 }.joined(separator: " ")).lineLimit(1).foregroundStyle(.secondary)
        }
    }
}

/// Tags that complete the word being typed at the end of a tags field; clicking one fills it in.
struct TagSuggestions: View {
    @Binding var text: String
    let tags: [String]

    var body: some View {
        let matches = Self.matches(for: text, in: tags)
        if !matches.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(matches, id: \.self) { tag in
                        Button("#" + tag) { text = Self.complete(text, with: tag) }
                            .buttonStyle(.bordered).controlSize(.small)
                    }
                }
            }
        }
    }

    /// The tag being typed at the end of the text, without '#', or nil when there is none yet.
    static func partial(_ text: String) -> String? {
        guard let last = text.split(omittingEmptySubsequences: false, whereSeparator: { $0 == " " || $0 == "," }).last else { return nil }
        let p = last.drop(while: { $0 == "#" }).lowercased()
        return p.isEmpty ? nil : p
    }

    static func matches(for text: String, in tags: [String]) -> [String] {
        guard let p = partial(text) else { return [] }
        let taken = Set(Record.parseTags(text))
        return Array(tags.filter { $0.hasPrefix(p) && $0 != p && !taken.contains($0) }.prefix(5))
    }

    static func complete(_ text: String, with tag: String) -> String {
        var words = text.split(separator: " ", omittingEmptySubsequences: false).map(String.init)
        words[words.count - 1] = tag
        return words.joined(separator: " ") + " "
    }
}

struct RecordRow: View {
    let record: Record
    let now: Int

    var body: some View {
        HStack {
            Text(Self.time(record.t1) + "–" + (record.isRunning ? "now" : Self.time(record.t2)))
                .font(.caption).monospacedDigit().foregroundStyle(.secondary)
                .frame(width: 90, alignment: .leading)
            Text(record.ds.isEmpty ? "(no description)" : record.ds).lineLimit(1)
            TagLine(tags: record.tags)
            Spacer()
            Text(Store.format(record.duration(now: now), seconds: false)).monospacedDigit()
        }
        .font(.callout)
    }

    static func time(_ t: Int) -> String {
        let d = Date(timeIntervalSince1970: TimeInterval(t))
        let f = DateFormatter()
        f.dateFormat = Calendar.current.isDateInToday(d) ? "HH:mm" : "E HH:mm"
        return f.string(from: d)
    }
}

struct EditRecordView: View {
    @EnvironmentObject var store: Store
    @Environment(\.dismiss) private var dismiss
    @State var record: Record
    @State private var start = Date()
    @State private var end = Date()
    @State private var running = false
    @State private var tagText = ""

    var body: some View {
        Form {
            TextField("Description", text: $record.ds)
            TextField("Tags", text: $tagText, prompt: Text("core-12 call"))
            TagSuggestions(text: $tagText, tags: store.tags)
            DatePicker("Start", selection: $start)
            Toggle("Running", isOn: $running)
            if !running { DatePicker("End", selection: $end) }
        }
        .padding()
        .frame(width: 360)
        .onAppear {
            start = Date(timeIntervalSince1970: TimeInterval(record.t1))
            end = Date(timeIntervalSince1970: TimeInterval(record.t2))
            running = record.isRunning
            tagText = record.tags.joined(separator: " ")
        }
        .toolbar {
            ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
            ToolbarItem(placement: .confirmationAction) {
                Button("Save") {
                    record.t1 = Int(start.timeIntervalSince1970)
                    record.t2 = running ? record.t1 : max(Int(end.timeIntervalSince1970), record.t1 + 1)
                    record.tags = Record.parseTags(tagText)
                    let r = record
                    Task { await store.update(r) }
                    dismiss()
                }
            }
        }
    }
}

enum SettingsSection: String, CaseIterable, Identifiable {
    case account = "Account", general = "General", reminders = "Reminders", about = "About"

    var id: Self { self }
    var icon: String {
        switch self {
        case .account: return "person.crop.circle"
        case .general: return "gearshape"
        case .reminders: return "bell"
        case .about: return "info.circle"
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject var store: Store
    @State private var openAtLogin = SMAppService.mainApp.status == .enabled
    @State private var loginError = ""
    @State private var url = ""
    @State private var username = ""
    @State private var password = ""
    @State private var status = ""
    @State private var busy = false
    @State private var section: SettingsSection? = .account

    var body: some View {
        // A sidebar of sections, the way System Settings goes.
        NavigationSplitView {
            List(SettingsSection.allCases, selection: $section) { s in
                Label(s.rawValue, systemImage: s.icon).tag(s)
            }
            .navigationSplitViewColumnWidth(170)
        } detail: {
            detail
        }
        .frame(minWidth: 600, idealWidth: 640, minHeight: 400, idealHeight: 440)
        .onAppear { url = store.serverURL; username = store.username }
        .task(id: store.serverURL) { store.serverVersion = (try? await store.api.version()) ?? "unreachable" }
    }

    @ViewBuilder private var detail: some View {
        switch section ?? .account {
        case .account:
            pane {
                Section("Account") {
                    if !store.signedIn {
                        TextField("Server", text: $url, prompt: Text("https://timetagger.example.com"))
                        TextField("Username", text: $username)
                            .textContentType(.username)
                        SecureField("Password", text: $password)
                            .textContentType(.password)
                            .onSubmit(signIn)
                        HStack {
                            if !status.isEmpty { Text(status).font(.caption).foregroundStyle(.red) }
                            Spacer()
                            if busy { ProgressView().controlSize(.small) }
                            Button("Sign In", action: signIn)
                                .keyboardShortcut(.defaultAction)
                                .disabled(busy || url.isEmpty || username.isEmpty || password.isEmpty)
                        }
                    } else {
                        LabeledContent("Server", value: store.serverURL)
                        LabeledContent("Signed in as", value: store.username.isEmpty ? "—" : store.username)
                        HStack {
                            Spacer()
                            Button("Sign Out") { Task { await store.signOut() } }
                        }
                    }
                }
                if store.signedIn { AccessSection() }
            }
        case .general:
            pane {
                Section("Time") {
                    Picker("Work time zone", selection: $store.workTimeZoneID) {
                        ForEach(TimeZone.knownTimeZoneIdentifiers, id: \.self) { Text($0).tag($0) }
                    }
                    Toggle("Show work time next to local time", isOn: $store.showWorkTime)
                    Toggle("Pause the running task while the Mac sleeps", isOn: $store.pauseOnSleep)
                }
                Section("General") {
                    Toggle("Open at login", isOn: $openAtLogin)
                        .onChange(of: openAtLogin) { on in setOpenAtLogin(on) }
                    if !loginError.isEmpty { Text(loginError).font(.caption).foregroundStyle(.red) }
                }
                Section("Tickets") {
                    TextField("Ticket URL", text: $store.ticketURL, prompt: Text("https://company.atlassian.net/browse/{key}"))
                    Text("A tag like #sm-1061 links to this URL with {key} = SM-1061.").font(.caption).foregroundStyle(.secondary)
                }
            }
        case .reminders:
            pane {
                Section("Reminders") {
                    Toggle("Remind me when nothing is tracked", isOn: $store.remindIdle)
                    if store.remindIdle {
                        Stepper("Working hours from \(store.workStartHour):00", value: $store.workStartHour, in: 0...23)
                        Stepper("to \(store.workEndHour):00, weekdays", value: $store.workEndHour, in: 1...24)
                    }
                }
            }
        case .about:
            pane {
                Section("About") {
                    LabeledContent("TimeTaggerBar", value: Store.appVersion)
                    LabeledContent("Server", value: store.serverVersion)
                    if let u = store.update {
                        Link("Version \(u.version) is available", destination: u.url)
                    } else {
                        HStack {
                            Button("Check for Updates") { Task { await store.checkForUpdate() } }
                            Text(store.updateStatus).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
    }

    private func pane(@ViewBuilder _ content: () -> some View) -> some View {
        Form { content() }.formStyle(.grouped)
    }

    private func setOpenAtLogin(_ on: Bool) {
        do {
            if on { try SMAppService.mainApp.register() } else { try SMAppService.mainApp.unregister() }
            loginError = ""
        } catch {
            loginError = error.localizedDescription
            openAtLogin = SMAppService.mainApp.status == .enabled
        }
    }

    private func signIn() {
        busy = true
        status = ""
        Task {
            do {
                try await store.signIn(url: url, username: username, password: password)
                password = ""
            } catch {
                status = error.localizedDescription
            }
            busy = false
        }
    }
}

struct ReportView: View {
    @EnvironmentObject var store: Store
    @State private var options = ReportOptions()
    @State private var rows: [ReportRow] = []
    @State private var copied = false
    @State private var loading = false

    private var builder: ReportBuilder {
        ReportBuilder(options: options, timeZone: options.workZone ? store.workTimeZone : .current)
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            Form {
                Picker("Period", selection: $options.period) {
                    ForEach(Period.allCases) { Text($0.rawValue).tag($0) }
                }
                TextField("Tags", text: $options.tags, prompt: Text("#work"))
                Picker("Grouping", selection: $options.grouping) {
                    ForEach(Grouping.allCases) { Text($0.rawValue).tag($0) }
                }
                Picker("Group by period", selection: $options.groupPeriod) {
                    ForEach(GroupPeriod.allCases) { Text($0.rawValue).tag($0) }
                }
                Picker("Time zone", selection: $options.workZone) {
                    Text("Work · \(store.workTimeZoneID)").tag(true)
                    Text("Local").tag(false)
                }
                Picker("Duration", selection: $options.duration) {
                    ForEach(DurationFormat.allCases) { Text($0.rawValue).tag($0) }
                }
                Toggle("Show records", isOn: $options.showRecords)
                Toggle("Exclude tags", isOn: $options.excludeTags)
                Toggle("Hide secondary tags", isOn: $options.hideSecondaryTags)
            }
            .formStyle(.grouped)
            .frame(width: 280)

            VStack(alignment: .leading, spacing: 0) {
                Text("Click any cell to edit it before copying. Edits only change the copied table, not your records.")
                    .font(.caption).foregroundStyle(.secondary).padding(10)
                Divider()
                ScrollView([.vertical, .horizontal]) {
                    Grid(alignment: .leading, horizontalSpacing: 4, verticalSpacing: 2) {
                        GridRow {
                            ForEach(builder.columns, id: \.self) { Text($0).font(.caption.weight(.semibold)).foregroundStyle(.secondary) }
                            Color.clear.frame(width: 20, height: 1)
                        }
                        ForEach($rows) { $row in
                            GridRow {
                                ForEach(row.cells.indices, id: \.self) { i in
                                    TextField("", text: $row.cells[i])
                                        .textFieldStyle(.plain)
                                        .fontWeight(row.isHeader ? .semibold : .regular)
                                        .frame(minWidth: i == row.cells.count - 1 ? 240 : 70)
                                }
                                Button { rows.removeAll { $0.id == row.id } } label: { Image(systemName: "xmark") }
                                    .buttonStyle(.borderless)
                                    .help("Remove row")
                                    .accessibilityLabel("Remove row")
                            }
                            .padding(.vertical, 3)
                            .background(row.isHeader ? Color.secondary.opacity(0.08) : .clear)
                        }
                    }
                    .monospacedDigit()
                    .padding(10)
                    Button {
                        rows.append(ReportRow(isHeader: false, cells: Array(repeating: "", count: builder.columns.count)))
                    } label: { Label("Add Row", systemImage: "plus") }
                    .buttonStyle(.link)
                    .padding(.horizontal, 10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .background(.background)
            .overlay(alignment: .topTrailing) {
                if loading { ProgressView().controlSize(.small).padding(10) }
            }
        }
        .frame(minWidth: 900, minHeight: 560)
        .toolbar {
            ToolbarItem {
                Button("Reset Edits") { Task { await generate() } }
                    .help("Discard cell edits and rebuild the table")
            }
            ToolbarItem {
                Button {
                    ReportBuilder.copy(columns: builder.columns, rows: rows)
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1) { copied = false }
                } label: {
                    Label(copied ? "Copied" : "Copy Table", systemImage: copied ? "checkmark" : "doc.on.doc")
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut("c", modifiers: [.command, .shift])
                .help("Copy the table (⇧⌘C)")
            }
        }
        .navigationTitle("Report")
        .task(id: options) { await generate() }
    }

    private func generate() async {
        loading = true
        defer { loading = false }
        // The period's days follow the report's time zone (the work zone by default).
        let (t1, t2) = options.period.range(in: builder.timeZone)
        do {
            let recs = try await store.api.records(from: t1, to: t2).filter { !$0.isDeleted }
            rows = builder.rows(recs, from: t1, to: t2)
        } catch {
            store.error = error.localizedDescription
        }
    }
}

struct HistoryView: View {
    @EnvironmentObject var store: Store
    @State private var search = ""
    @State private var editing: Record?
    @StateObject private var feed = DayFeed()
    /// Server-side matches for the search, across all time.
    @State private var found: [Record]?

    var body: some View {
        let days = found.map(DayFeed.group) ?? feed.days()
        List {
            ForEach(days) { day in
                Section {
                    ForEach(day.records) { r in
                        row(r)
                            .contentShape(Rectangle())
                            .onTapGesture(count: 2) { editing = r }
                            .contextMenu {
                                Button("Edit…") { editing = r }
                                Button("Resume") { Task { await store.start(r.ds, tags: r.tags) } }
                                if r.isRunning { Button("Stop") { Task { await store.stop(r) } } }
                                TicketLinks(record: r)
                                Divider()
                                Button("Delete", role: .destructive) { Task { await store.delete(r) } }
                            }
                    }
                } header: {
                    HStack {
                        Text(day.id, format: .dateTime.weekday(.wide).day().month(.wide))
                        Spacer()
                        Text(Store.format(day.records.reduce(0) { $0 + $1.duration(now: store.now) }, seconds: false))
                            .monospacedDigit()
                    }
                }
            }
            // Scrolling to the end reaches further back.
            if found == nil && !feed.reachedEnd {
                ProgressView().controlSize(.small).frame(maxWidth: .infinity)
                    .onAppear { Task { await load { try await feed.loadMore(store.api) } } }
            }
        }
        .overlay {
            if days.isEmpty && (found != nil || feed.reachedEnd) { Text("No records").foregroundStyle(.secondary) }
        }
        .searchable(text: $search, prompt: "Search description or tag")
        .toolbar {
            ToolbarItemGroup {
                Button {
                    let t = Int(Date().timeIntervalSince1970)
                    editing = Record(key: Record.newKey(), rev: 0, t1: t - 3600, t2: t, ds: "", deleted: 0)
                } label: { Label("Add Record", systemImage: "plus") }
                .keyboardShortcut("n", modifiers: .command)
                .help("Add a record (⌘N)")
            }
        }
        .navigationTitle("History")
        .frame(minWidth: 620, minHeight: 480)
        .sheet(item: $editing) { r in
            EditRecordView(record: r).environmentObject(store)
        }
        .task(id: store.lately.hashValue) { await load { try await feed.reload(store.api) } }
        .task(id: "\(search)-\(store.lately.hashValue)") {
            let q = search.trimmingCharacters(in: .whitespaces)
            guard !q.isEmpty else { found = nil; return }
            try? await Task.sleep(nanoseconds: 300_000_000)   // let the typing settle
            guard !Task.isCancelled else { return }
            await load { found = try await store.api.search(q).filter { !$0.isDeleted } }
        }
    }

    private func row(_ r: Record) -> some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(store.clock(r.t1) + "–" + (r.isRunning ? "now" : store.clock(r.t2)))
                if store.showsWorkZone {
                    Text(store.clock(r.t1, work: true) + "–" + (r.isRunning ? "now" : store.clock(r.t2, work: true)) + " " + store.workZoneName)
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            .monospacedDigit()
            .frame(width: 150, alignment: .leading)
            Text(r.ds.isEmpty ? "(no description)" : r.ds).lineLimit(2)
            Spacer()
            if r.isRunning { Image(systemName: "circle.fill").foregroundStyle(.red).font(.caption2).accessibilityLabel("Running") }
            Text(Store.format(r.duration(now: store.now), seconds: false)).monospacedDigit()
        }
        .padding(.vertical, 2)
    }

    private func load(_ op: () async throws -> Void) async {
        do { try await op() } catch { store.error = error.localizedDescription }
    }
}
