import Foundation

indirect enum J: Codable, Equatable {
    case null, bool(Bool), number(Double), string(String), array([J]), object([String: J])

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode([J].self) { self = .array(v) }
        else { self = .object(try c.decode([String: J].self)) }
    }
    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .null: try c.encodeNil()
        case .bool(let v): try c.encode(v)
        case .number(let v): try c.encode(v)
        case .string(let v): try c.encode(v)
        case .array(let v): try c.encode(v)
        case .object(let v): try c.encode(v)
        }
    }
    var object: [String: J] { if case .object(let v) = self { return v }; return [:] }
    var array: [J] { if case .array(let v) = self { return v }; return [] }
    var text: String { if case .string(let v) = self { return v }; return "" }
    var double: Double? {
        switch self { case .number(let v): return v; case .string(let v): return Double(v); default: return nil }
    }
    var flag: Bool { if case .bool(let v) = self { return v }; return false }
    subscript(_ key: String) -> J {
        get { object[key] ?? .null }
        set { var values = object; values[key] = newValue; self = .object(values) }
    }
    subscript(_ index: Int) -> J {
        get { array.indices.contains(index) ? array[index] : .null }
        set { var values = array; if values.indices.contains(index) { values[index] = newValue }; self = .array(values) }
    }
    func at(_ path: [String]) -> J { path.reduce(self) { $0[$1] } }
    mutating func set(_ path: [String], _ value: J) {
        guard let head = path.first else { self = value; return }
        var child = self[head]; child.set(Array(path.dropFirst()), value); self[head] = child
    }
    func encoded() throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(self)
    }
    static func decode(_ data: Data) throws -> J { try JSONDecoder().decode(J.self, from: data) }
    static func numbers(_ values: [String: Double]) -> J { .object(values.mapValues(J.number)) }
}

struct CalculationError: LocalizedError {
    var message: String
    init(_ message: String) { self.message = message }
    var errorDescription: String? { message }
}

func n(_ value: Double) -> String { String(format: "%.1f", locale: Locale(identifier: "en_US_POSIX"), value) }
func rounded1(_ value: Double) -> Double { Double(n(value)) ?? value }

enum Phase: String, CaseIterable, Identifiable, Hashable {
    case takeoff, landing, cruise, climb
    var id: String { rawValue }
    var title: String { rawValue.capitalized }
}

struct MathGrid {
    var axis = "PA / OAT"
    var lowX: Double, highX: Double, lowY: Double, highY: Double
    var q11: Double, q12: Double, q21: Double, q22: Double
}
struct MathStep: Identifiable {
    let id = UUID()
    var title: String
    var formula: String
    var value: String
    var grid: MathGrid? = nil
}
struct Calculation {
    var result: J
    var steps: [MathStep]
}
