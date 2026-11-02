import SwiftUI
import UniformTypeIdentifiers

@MainActor
struct DatasetEditor: View {
    @EnvironmentObject var store: NativeStore
    @Binding var table: J
    var phase: String
    var model: String
    var year: Double?
    @State private var importing = false
    @State private var exporting = false
    @State private var document: PPLDocument?
    @State private var pasted = ""
    @State private var error: String?
    @State private var replacing = false
    private var mode: String { table["mode"].text }
    private var issues: [String] {
        do { return try NativeValidation.dataset(table, phase: phase, model: model).1 }
        catch { return [error.localizedDescription] }
    }
    private func binding(_ key: String) -> Binding<String> {
        Binding(get: { jsonText(table[key]) }, set: { table[key] = .string($0) })
    }
    private var modeBinding: Binding<String> {
        Binding(get: { mode }, set: { value in
            table["mode"] = .string(value)
            if value == "c172m1974", let reference = store.engine?.data["reference"][phase] {
                table["source"] = reference["source_url"]; table["conditions"] = reference["conditions"]
            }
        })
    }
    var body: some View {
        Form {
            Section(store.label("Data source", "数据来源")) {
                Picker(store.label("Mode", "模式"), selection: modeBinding) {
                    Text(store.label("Not configured", "未配置")).tag("none")
                    Text(store.label("Manual POH table", "手动 POH 表")).tag("manual")
                    if model == "c172n" { Text("C172N built-in").tag("builtin") }
                    if model == "c172m" && phase != "climb" { Text("1974 C172M reference").tag("c172m1974").disabled(year != 1974) }
                }
                .accessibilityIdentifier("poh-mode-" + phase)
                TextField(store.label("POH edition / figure / page", "POH 版本／图号／页码"), text: binding("source"), axis: .vertical)
                TextField(store.label("Conditions", "适用条件"), text: binding("conditions"), axis: .vertical)
                if issues.isEmpty { Label(store.label("Table ready", "表格可用"), systemImage: "checkmark.circle").foregroundStyle(.green) }
                else { ForEach(Array(issues.prefix(8).enumerated()), id: \.offset) { _, issue in Text(issue).font(.caption).foregroundStyle(.orange) } }
            }
            if mode == "manual" {
                if phase == "cruise" {
                    Section { NumberRow(title: store.label("Reference weight", "参考重量"), unit: "lb", text: binding("reference_weight_lb")) }
                } else if phase == "climb" { climbRulesSection }
                else { rulesSection }
                Section(store.label("POH rows", "POH 数据行")) {
                    ForEach(Array(table["rows"].array.enumerated()), id: \.offset) { index, row in
                        NavigationLink {
                            POHRowEditor(row: Binding(get: { table["rows"][index] }, set: { table["rows"][index] = $0 }), phase: phase, index: index)
                        } label: {
                            VStack(alignment: .leading, spacing: 5) {
                                Text("\(index + 1). " + (NativeValidation.columns[phase] ?? []).prefix(3).map { key in key + " " + (row[key].double.map(n) ?? "—") }.joined(separator: " · "))
                                    .font(.subheadline).monospacedDigit()
                                Text((NativeValidation.columns[phase] ?? []).dropFirst(3).map { row[$0].double.map(n) ?? "—" }.joined(separator: " / ")).font(.caption).foregroundStyle(.secondary)
                            }
                        }.swipeActions { Button(role: .destructive) { var rows = table["rows"].array; rows.remove(at: index); table["rows"] = .array(rows) } label: { Image(systemName: "trash") } }
                    }
                    Button {
                        var rows = table["rows"].array
                        rows.append(.object(Dictionary(uniqueKeysWithValues: (NativeValidation.columns[phase] ?? []).map { ($0, J.null) })))
                        table["rows"] = .array(rows)
                    } label: { Label(store.label("Add row", "添加行"), systemImage: "plus") }
                    .disabled(table["rows"].array.count >= 3000)
                }
                Section("CSV / TSV") {
                    Button { importing = true } label: { Label(store.label("Replace rows from file", "从文件替换数据行"), systemImage: "square.and.arrow.down") }
                    Button { export(rows: table["rows"].array) } label: { Label(store.label("Export CSV", "导出 CSV"), systemImage: "square.and.arrow.up") }
                    Button { export(rows: []) } label: { Label(store.label("CSV template", "CSV 模板"), systemImage: "doc") }
                    DisclosureGroup(store.label("Paste table", "粘贴表格")) {
                        TextEditor(text: $pasted).font(.system(.caption, design: .monospaced)).frame(minHeight: 140)
                        Button { replaceRows(pasted) } label: { Label(store.label("Replace rows", "替换数据行"), systemImage: "arrow.down.doc") }.disabled(pasted.isEmpty)
                    }
                    if model == "c172n" { Button("Copy C172N table", systemImage: "doc.on.doc") { replacing = true } }
                }
            }
            if mode == "builtin" || mode == "c172m1974" {
                Section(store.label("Original table", "原始表格")) {
                    if mode == "c172m1974" {
                        Text(store.engine?.data["reference"][phase]["conditions"].text ?? "").font(.caption).foregroundStyle(.orange)
                    }
                    POHTable(phase: phase, reference: mode == "c172m1974")
                    if mode == "builtin" { Button("Copy into manual table", systemImage: "doc.on.doc") { replacing = true } }
                }
            }
            if let error { Section { Text(error).foregroundStyle(.red) } }
        }
        .navigationTitle(phase.capitalized + " POH")
        .confirmationDialog("Replace this phase with the C172N table?", isPresented: $replacing, titleVisibility: .visible) {
            Button("Replace table", role: .destructive) { if let value = store.engine?.data["builtin"][phase] { table = value } }
        }
        .fileImporter(isPresented: $importing, allowedContentTypes: [.commaSeparatedText, .plainText, .text], allowsMultipleSelection: false) { result in
            do {
                guard let url = try result.get().first else { return }
                let access = url.startAccessingSecurityScopedResource(); defer { if access { url.stopAccessingSecurityScopedResource() } }
                let data = try Data(contentsOf: url)
                guard data.count <= 1_000_000, let text = String(data: data, encoding: .utf8) else { throw CalculationError("Use a UTF-8 CSV/TSV smaller than 1 MB") }
                replaceRows(text)
            } catch { self.error = error.localizedDescription }
        }
        .fileExporter(isPresented: $exporting, document: document, contentType: .commaSeparatedText, defaultFilename: phase + "-poh") { result in
            if case .failure(let error) = result { self.error = error.localizedDescription }
        }
    }
    private var rulesSection: some View {
        Section(store.label("POH correction rules", "POH 修正规则")) {
            ForEach(["headwind", "tailwind"], id: \.self) { kind in
                NumberRow(title: kind.capitalized + " change", unit: "%", text: binding(kind + "_pct"))
                NumberRow(title: kind.capitalized + " knot step", unit: "kt", text: binding(kind + "_step_kt"))
                NumberRow(title: kind.capitalized + " maximum", unit: "kt", text: binding(kind + "_max_kt"))
            }
            Picker("Grass", selection: binding("grass_mode")) {
                Text("No recorded rule").tag("none")
                Text("Ground-roll add to both").tag("ground_add")
                Text("Increase each distance").tag("both_percent")
            }
            if table["grass_mode"].text != "none" { NumberRow(title: "Grass change", unit: "%", text: binding("grass_pct")) }
        }
    }
    private var climbRulesSection: some View {
        Section(store.label("POH climb correction rules", "POH 爬升修正规则")) {
            NumberRow(title: store.label("Warm-temperature increase", "高温增加比例"), unit: "%", text: binding("warm_temp_pct"))
            NumberRow(title: store.label("Above-standard temperature step", "高于标准温度的间隔"), unit: "°C", text: binding("warm_temp_step_c"))
                .disabled(table["warm_temp_pct"].double == 0)
            NumberRow(title: store.label("Start / taxi / takeoff fuel", "启动／滑行／起飞用油"), unit: "US gal", text: binding("start_taxi_takeoff_fuel_gal"))
        }
    }
    private func replaceRows(_ text: String) {
        do {
            let rows = try NativeCSV.read(text, phase: phase)
            var candidate = table; candidate["rows"] = .array(rows); candidate["mode"] = .string("manual")
            table = try NativeValidation.dataset(candidate, phase: phase, model: model).0
            error = nil
        } catch { self.error = error.localizedDescription }
    }
    private func export(rows: [J]) { document = PPLDocument(data: NativeCSV.write(rows, phase: phase)); exporting = true }
}

struct POHRowEditor: View {
    @EnvironmentObject var store: NativeStore
    @Binding var row: J
    var phase: String
    var index: Int
    @FocusState private var keyboard: Bool
    var body: some View {
        Form {
            ForEach(NativeValidation.columns[phase] ?? [], id: \.self) { key in
                NumberRow(title: fieldName(key, chinese: store.chinese), unit: unitFor(key), text: Binding(get: { jsonText(row[key]) }, set: { row[key] = .string($0) })).focused($keyboard)
            }
        }.navigationTitle("POH row \(index + 1)")
            .toolbar { ToolbarItemGroup(placement: .keyboard) { Spacer(); Button("Done") { keyboard = false; endNativeEditing() } } }
    }
}

@MainActor
struct POHTable: View {
    @EnvironmentObject var store: NativeStore
    var phase: String
    var reference: Bool
    var body: some View {
        let source = store.engine?.data[reference ? "reference" : "builtin"][phase] ?? .null
        let columns = reference ? source["columns"].array.map(\.text) : NativeValidation.columns[phase] ?? []
        let rows = source["rows"].array
        ScrollView(.horizontal) {
            LazyVStack(alignment: .leading, spacing: 10) {
                HStack { ForEach(columns, id: \.self) { Text($0).font(.caption).frame(width: 105, alignment: .trailing) } }
                ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                    HStack {
                        ForEach(Array(columns.enumerated()), id: \.offset) { index, key in
                            Text((reference ? row[index] : row[key]).double.map(n) ?? "—").monospacedDigit().frame(width: 105, alignment: .trailing)
                        }
                    }.font(.subheadline)
                    Divider()
                }
            }.padding(.vertical, 4)
        }
    }
}
