import SwiftUI
import UniformTypeIdentifiers

struct ProfileSheet: Identifiable {
    let id = UUID()
    var profile: J
}

@MainActor
struct AircraftListView: View {
    @EnvironmentObject var store: NativeStore
    @State private var newProfile: ProfileSheet?
    @State private var importing = false
    @State private var exporting = false
    @State private var document: PPLDocument?
    @State private var deleting: String?
    var body: some View {
        List {
            Section { AircraftSelection() }
            Section(store.label("Saved aircraft", "已保存飞机")) {
                ForEach(Array(store.profiles.enumerated()), id: \.offset) { _, profile in
                    NavigationLink {
                        AircraftEditor(profile: profile)
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(profile["registration"].text.isEmpty ? profile["name"].text : profile["registration"].text).font(.headline)
                            Text(profile["name"].text).font(.subheadline).foregroundStyle(.secondary)
                            if !store.issues(profile).isEmpty { Text(store.label("W&B draft", "W&B 待补齐")).font(.caption).foregroundStyle(.orange) }
                        }
                    }
                    .swipeActions {
                        Button(role: .destructive) { deleting = profile["id"].text } label: { Label("Delete", systemImage: "trash") }
                    }
                }
            }
        }
        .navigationTitle(store.label("Aircraft", "飞机档案"))
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button { importing = true } label: { Image(systemName: "square.and.arrow.down") }.accessibilityLabel("Import aircraft backup")
                Button {
                    do { document = PPLDocument(data: try store.backup()); exporting = true }
                    catch { store.errorMessage = error.localizedDescription }
                } label: { Image(systemName: "square.and.arrow.up") }.accessibilityLabel("Export aircraft backup")
                Menu {
                    ForEach(Array((store.engine?.data["catalogue"].array ?? []).enumerated()), id: \.offset) { _, model in
                        Button(model["name"].text) { newProfile = ProfileSheet(profile: model["template"]) }
                    }
                } label: { Image(systemName: "plus") }.accessibilityLabel("New aircraft")
            }
        }
        .sheet(item: $newProfile) { sheet in NavigationStack { AircraftEditor(profile: sheet.profile) } }
        .confirmationDialog(store.label("Delete aircraft?", "删除飞机档案？"), isPresented: Binding(get: { deleting != nil }, set: { if !$0 { deleting = nil } })) {
            Button(store.label("Delete", "删除"), role: .destructive) {
                do { if let deleting { try store.delete(deleting) }; deleting = nil }
                catch { store.errorMessage = error.localizedDescription }
            }
        }
        .fileImporter(isPresented: $importing, allowedContentTypes: [.json], allowsMultipleSelection: false) { result in
            do {
                guard let url = try result.get().first else { return }
                let access = url.startAccessingSecurityScopedResource(); defer { if access { url.stopAccessingSecurityScopedResource() } }
                try store.importBackup(Data(contentsOf: url))
            } catch { store.errorMessage = error.localizedDescription }
        }
        .fileExporter(isPresented: $exporting, document: document, contentType: .json, defaultFilename: "ppl-aircraft-backup") { result in
            if case .failure(let error) = result { store.errorMessage = error.localizedDescription }
        }
    }
}

func jsonText(_ value: J) -> String {
    if case .string(let text) = value { return text }
    if let number = value.double { return String(number) }
    return ""
}

@MainActor
struct AircraftEditor: View {
    @EnvironmentObject var store: NativeStore
    @Environment(\.dismiss) private var dismiss
    @State private var draft: J
    @State private var error: String?
    @State private var changingModel = false
    @State private var copySheet: ProfileSheet?
    @FocusState private var keyboard: Bool
    init(profile: J) { _draft = State(initialValue: profile) }
    private func binding(_ path: [String]) -> Binding<String> {
        Binding(get: { jsonText(draft.at(path)) }, set: { draft.set(path, .string($0)) })
    }
    private func number(_ title: String, _ path: [String], _ unit: String) -> some View {
        NumberRow(title: title, unit: unit, text: binding(path)).focused($keyboard)
    }
    var body: some View {
        Form {
            Section(store.label("Identity", "飞机身份")) {
                TextField(store.label("Aircraft name", "飞机名称"), text: binding(["name"]))
                TextField(store.label("Registration", "注册号"), text: binding(["registration"])).textInputAutocapitalization(.characters)
                LabeledContent("Model", value: draft["model_id"].text.uppercased())
                TextField(store.label("Serial number", "序列号"), text: binding(["serial_number"]))
                number(store.label("Model year", "制造年份"), ["year"], "")
                TextField(store.label("W&B / POH document reference", "称重记录／POH 来源"), text: binding(["wb_reference"]), axis: .vertical)
                TextField(store.label("Document date", "文件日期"), text: binding(["wb_date"]))
                TextField(store.label("Configuration / STC notes", "配置／STC 备注"), text: binding(["notes"]), axis: .vertical).lineLimit(3...8)
            }
            Section(store.label("Empty aircraft and limits", "空机与限制")) {
                ForEach(NativeValidation.wbFields, id: \.self) { key in
                    number(fieldName(key, chinese: store.chinese), ["wb", key], key.contains("moment") ? "lb-in" : key.contains("density") ? "lb/gal" : key.contains("arm") ? "in" : key.contains("gal") ? "US gal" : "lb")
                }
                if let weight = draft["wb"]["empty_weight_lb"].double, let moment = draft["wb"]["empty_moment_lb_in"].double, weight > 0 {
                    LabeledContent(store.label("Empty CG", "空机重心"), value: n(moment / weight) + " in")
                }
            }
            Section(store.label("Loading stations", "装载站位")) {
                ForEach(Array(draft["wb"]["stations"].array.enumerated()), id: \.offset) { index, station in
                    DisclosureGroup(station["label"].text) {
                        Toggle(store.label("Enabled", "启用"), isOn: Binding(get: { draft["wb"]["stations"][index]["enabled"].flag }, set: { draft["wb"]["stations"][index]["enabled"] = .bool($0) }))
                        stationNumber(index, key: "arm_in", title: store.label("Arm", "力臂"), unit: "in")
                        stationNumber(index, key: "max_weight_lb", title: store.label("Station limit", "站位限制"), unit: "lb")
                    }
                }
            }
            Section("CG envelope / 重心包线") {
                ForEach(Array(draft["wb"]["cg_limits"].array.enumerated()), id: \.offset) { index, _ in
                    VStack {
                        envelopeNumber(index, key: "weight_lb", title: "Weight", unit: "lb")
                        envelopeNumber(index, key: "forward_in", title: "Forward", unit: "in")
                        envelopeNumber(index, key: "aft_in", title: "Aft", unit: "in")
                    }
                    .swipeActions { Button(role: .destructive) { var rows = draft["wb"]["cg_limits"].array; rows.remove(at: index); draft["wb"]["cg_limits"] = .array(rows) } label: { Image(systemName: "trash") } }
                }
                Button { var rows = draft["wb"]["cg_limits"].array; rows.append(.object(["weight_lb": .null, "forward_in": .null, "aft_in": .null])); draft["wb"]["cg_limits"] = .array(rows) } label: { Label(store.label("Add CG row", "添加重心行"), systemImage: "plus") }
                .disabled(draft["wb"]["cg_limits"].array.count >= 30)
            }
            Section("POH performance / 性能数据") {
                ForEach(NativeValidation.phases, id: \.self) { phase in
                    NavigationLink(phase.capitalized) {
                        DatasetEditor(table: Binding(get: { draft["performance"][phase] }, set: { draft["performance"][phase] = $0 }), phase: phase, model: draft["model_id"].text, year: draft["year"].double)
                    }
                }
            }
            Section {
                Button {
                    var copy = draft; copy["id"] = .string(""); copy["name"] = .string(draft["name"].text + " (copy)")
                    for key in ["registration", "serial_number", "wb_reference", "wb_date"] { copy[key] = .string("") }
                    copy["wb"]["empty_weight_lb"] = .null; copy["wb"]["empty_moment_lb_in"] = .null
                    copySheet = ProfileSheet(profile: copy)
                } label: { Label(store.label("Duplicate as new aircraft", "复制为新飞机"), systemImage: "doc.on.doc") }
                Button(store.label("Change model…", "更换机型…"), role: .destructive) { changingModel = true }
            }
            if let error { Section { Text(error).foregroundStyle(.red) } }
        }
        .navigationTitle(draft["registration"].text.isEmpty ? store.label("Aircraft draft", "飞机草稿") : draft["registration"].text)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) { Button(store.label("Save", "保存")) {
                do { keyboard = false; try store.save(draft); dismiss() }
                catch { self.error = error.localizedDescription }
            }.accessibilityIdentifier("save-aircraft") }
            ToolbarItemGroup(placement: .keyboard) { Spacer(); Button(store.label("Done", "完成")) { keyboard = false } }
        }
        .sheet(item: $copySheet) { sheet in NavigationStack { AircraftEditor(profile: sheet.profile) } }
        .confirmationDialog(store.label("Changing model resets W&B and POH data", "更换机型会重置称重与性能数据"), isPresented: $changingModel, titleVisibility: .visible) {
            ForEach(Array((store.engine?.data["catalogue"].array ?? []).enumerated()), id: \.offset) { _, model in
                Button(model["name"].text) {
                    var next = model["template"]
                    for key in ["id", "registration", "serial_number", "year", "wb_reference", "wb_date", "notes"] { next[key] = draft[key] }
                    draft = next
                }
            }
        }
    }
    private func stationNumber(_ index: Int, key: String, title: String, unit: String) -> some View {
        NumberRow(title: title, unit: unit, text: Binding(get: { jsonText(draft["wb"]["stations"][index][key]) }, set: { draft["wb"]["stations"][index][key] = .string($0) })).focused($keyboard)
    }
    private func envelopeNumber(_ index: Int, key: String, title: String, unit: String) -> some View {
        NumberRow(title: title, unit: unit, text: Binding(get: { jsonText(draft["wb"]["cg_limits"][index][key]) }, set: { draft["wb"]["cg_limits"][index][key] = .string($0) })).focused($keyboard)
    }
}
