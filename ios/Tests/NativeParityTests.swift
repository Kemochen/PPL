import XCTest
@testable import PPL

final class NativeParityTests: XCTestCase {
    func testSwiftMatchesExistingCalculators() throws {
        let engine = try NativeEngine()
        let url = try XCTUnwrap(Bundle(for: Self.self).url(forResource: "NativeParity", withExtension: "json"))
        let cases = try J.decode(Data(contentsOf: url)).array
        XCTAssertGreaterThan(cases.count, 60)
        for sample in cases {
            let name = sample["name"].text
            let phase = String(sample["path"].text.split(separator: "/").last!)
            if sample["expected"]["status"].double != 200 {
                XCTAssertThrowsError(try engine.calculate(phase, form: sample["body"]), name)
            } else {
                do {
                    let actual = try engine.calculate(phase, form: sample["body"])
                    compare(actual.result, sample["expected"]["body"]["result"], path: name)
                    XCTAssertFalse(actual.steps.isEmpty, name + " must include calculation steps")
                } catch { XCTFail(name + ": " + error.localizedDescription) }
            }
        }
    }
    private func compare(_ actual: J, _ expected: J, path: String) {
        switch expected {
        case .number(let value):
            guard let number = actual.double else { XCTFail("Missing numeric result: " + path); return }
            XCTAssertEqual(number, value, accuracy: max(abs(value), 1) * 1e-9, path)
        case .object(let values): for (key, value) in values { compare(actual[key], value, path: path + "." + key) }
        case .array(let values):
            XCTAssertEqual(actual.array.count, values.count, path)
            for (index, value) in values.enumerated() { compare(actual[index], value, path: path + ".\(index)") }
        case .null: XCTAssertEqual(actual, .null, path)
        case .bool(let value): XCTAssertEqual(actual.flag, value, path)
        case .string:
            if ["status", "phase", "item", "kind", "registration", "aircraft_name"].contains(path.split(separator: ".").last.map { String($0) } ?? "") { XCTAssertEqual(actual.text, expected.text, path) }
        }
    }
    func testNonfiniteInputsAndMissingCellsAreRejected() throws {
        let engine = try NativeEngine()
        XCTAssertThrowsError(try engine.calculate("takeoff", form: .object(["weight_lbs": .number(2300), "oat_c": .string("nan")])))
        var profile = engine.data["profiles"][0]
        profile["performance"]["takeoff"] = engine.data["builtin"]["takeoff"]
        var rows = profile["performance"]["takeoff"]["rows"].array; rows.removeFirst()
        profile["performance"]["takeoff"]["rows"] = .array(rows)
        XCTAssertThrowsError(try engine.calculate("takeoff", form: .numbers(["weight_lbs": 2300, "pressure_altitude_ft": 0, "oat_c": 0]), profile: profile))
    }
    func testGridUsesPAThenOATAndExactCellsAvoidDivisionByZero() throws {
        let engine = try NativeEngine()
        let rows = engine.data["builtin"]["takeoff"]["rows"].array.filter { $0["weight_lb"].double == 2300 }
        let exact = try NativeEngine.grid(rows, field: "ground_ft", x: 2000, y: 20, label: "Ground")
        XCTAssertEqual(exact.0, 1000)
        XCTAssertEqual(exact.1.grid?.axis, "PA / OAT")
        XCTAssertEqual(exact.1.grid?.q11, 1000)
        XCTAssertFalse(exact.1.value.contains("nan"))
    }
}
