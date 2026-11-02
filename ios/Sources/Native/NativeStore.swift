import Foundation
import Combine
import SwiftUI
import UniformTypeIdentifiers
import TabularData

@MainActor
final class NativeStore: ObservableObject {
    @Published private(set) var profiles: [J] = []
    @Published private(set) var activeID = ""
    @Published var chinese = false
    @Published var errorMessage: String?
    @Published var startupError: String?
    let engine: NativeEngine?
    private let file: URL
    private var storageLocked = false

    init(directory: URL? = nil, engine provided: NativeEngine? = nil) {
        let directory = directory ?? FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        file = directory.appendingPathComponent("native-aircraft-v1.json")
        do { engine = try provided ?? NativeEngine() }
        catch { engine = nil; startupError = error.localizedDescription }
        guard let engine else { return }
        do {
            if FileManager.default.fileExists(atPath: file.path) {
                let value = try J.decode(Data(contentsOf: file))
                guard value["version"].double == 1, case .array = value["profiles"], value["profiles"].array.count <= 100 else { throw CalculationError("Unsupported saved profile version / structure") }
                profiles = try value["profiles"].array.map { try NativeValidation.profile($0, catalogue: engine.data["catalogue"]).0 }
                activeID = value["activeId"].text
                chinese = value["chinese"].flag
                if !profiles.contains(where: { $0["id"].text == activeID }) { activeID = profiles.first?["id"].text ?? "" }
            } else {
                profiles = try engine.data["profiles"].array.map { try NativeValidation.profile($0, catalogue: engine.data["catalogue"]).0 }
                activeID = profiles.first?["id"].text ?? ""
                try persist(profiles, active: activeID)
            }
        } catch {
            storageLocked = true
            errorMessage = "Saved aircraft could not be read. The existing file has not been overwritten. " + error.localizedDescription
        }
    }

    var activeProfile: J? { profiles.first { $0["id"].text == activeID } }
    var displayProfile: J { activeProfile ?? .null }
    func label(_ en: String, _ zh: String) -> String { chinese ? zh : en }
    func issues(_ profile: J) -> [String] { (try? NativeValidation.profile(profile, catalogue: engine?.data["catalogue"] ?? .null).1) ?? ["Invalid profile"] }
    private func persist(_ next: [J], active: String) throws {
        guard !storageLocked else { throw CalculationError("Existing saved data is unreadable; it has not been overwritten.") }
        try FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
        let value = J.object(["version": .number(1), "profiles": .array(next), "activeId": .string(active), "chinese": .bool(chinese)])
        try value.encoded().write(to: file, options: .atomic)
    }
    func select(_ id: String) {
        guard profiles.contains(where: { $0["id"].text == id }) else { return }
        do { try persist(profiles, active: id); activeID = id }
        catch { errorMessage = error.localizedDescription }
    }
    func toggleLanguage() {
        chinese.toggle()
        do { try persist(profiles, active: activeID) }
        catch { errorMessage = error.localizedDescription }
    }
    func save(_ draft: J) throws {
        guard let engine else { throw CalculationError("Missing native engine") }
        var profile = try NativeValidation.profile(draft, catalogue: engine.data["catalogue"]).0
        if profile["id"].text.isEmpty { profile["id"] = .string(UUID().uuidString) }
        var next = profiles.filter { $0["id"] != profile["id"] }
        next.append(profile)
        guard next.count <= 100 else { throw CalculationError("Maximum 100 aircraft profiles") }
        let active = activeProfile == nil ? profile["id"].text : activeID
        try persist(next, active: active); profiles = next; activeID = active
    }
    func delete(_ id: String) throws {
        let next = profiles.filter { $0["id"].text != id }
        let active = activeID == id ? next.first?["id"].text ?? "" : activeID
        try persist(next, active: active); profiles = next; activeID = active
    }
    func importBackup(_ data: Data) throws {
        guard data.count <= 2_000_000, let engine else { throw CalculationError("Backup must be smaller than 2 MB") }
        let backup = try J.decode(data)
        guard backup["version"].double == 1, !backup["profiles"].array.isEmpty,
              backup["profiles"].array.count + profiles.count <= 100 else { throw CalculationError("Invalid aircraft backup (version 1, maximum 100 aircraft)") }
        let imported = try backup["profiles"].array.map { raw -> J in
            var value = try NativeValidation.profile(raw, catalogue: engine.data["catalogue"]).0
            value["id"] = .string(UUID().uuidString); return value
        }
        let next = profiles + imported
        let active = activeProfile == nil ? imported[0]["id"].text : activeID
        try persist(next, active: active); profiles = next; activeID = active
    }
    func backup() throws -> Data { try J.object(["version": .number(1), "profiles": .array(profiles)]).encoded() }
}

struct PPLDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.json, .commaSeparatedText, .plainText] }
    var data: Data
    init(data: Data) { self.data = data }
    init(configuration: ReadConfiguration) throws {
        guard let data = configuration.file.regularFileContents else { throw CalculationError("Unable to read file") }
        self.data = data
    }
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper { FileWrapper(regularFileWithContents: data) }
}

enum NativeCSV {
    static func read(_ text: String, phase: String) throws -> [J] {
        guard text.utf8.count <= 1_000_000, let expected = NativeValidation.columns[phase] else { throw CalculationError("Choose a POH phase and a table smaller than 1 MB") }
        let clean = text.trimmingCharacters(in: .whitespacesAndNewlines).replacingOccurrences(of: "\u{feff}", with: "")
        let delimiter: Character = clean.split(separator: "\n").first?.contains("\t") == true ? "\t" : ","
        let frame = try DataFrame(csvData: Data(clean.utf8), types: Dictionary(uniqueKeysWithValues: expected.map { ($0, CSVType.double) }), options: CSVReadingOptions(hasHeaderRow: true, delimiter: delimiter))
        guard frame.columns.count == expected.count, Set(frame.columns.map(\.name)) == Set(expected), !frame.rows.isEmpty, frame.rows.count <= 3000 else { throw CalculationError("Expected header: " + expected.joined(separator: ",")) }
        return try frame.rows.map { row in
            var values: [String: J] = [:]
            for key in expected {
                guard let value = row[key] as? Double, value.isFinite else { throw CalculationError("Every CSV cell must contain a finite number: " + key) }
                values[key] = .number(value)
            }
            return .object(values)
        }
    }
    static func write(_ rows: [J], phase: String) -> Data {
        let columns = NativeValidation.columns[phase] ?? []
        let lines = [columns.joined(separator: ",")] + rows.map { row in columns.map { row[$0].double.map { String($0) } ?? "" }.joined(separator: ",") }
        return Data((lines.joined(separator: "\r\n") + "\r\n").utf8)
    }
}
