import XCTest
@testable import PPL

final class NativeStoreTests: XCTestCase {
    @MainActor
    func testBackupPersistenceAndFullPrecision() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let engine = try NativeEngine(), store = NativeStore(directory: directory, engine: engine)
        var profile = try XCTUnwrap(store.activeProfile)
        profile["wb"]["empty_moment_lb_in"] = .number(58866.23456789)
        try store.save(profile)
        let reload = NativeStore(directory: directory, engine: engine)
        XCTAssertEqual(reload.activeProfile?["wb"]["empty_moment_lb_in"].double, 58866.23456789)
        let backup = try reload.backup()
        try reload.importBackup(backup)
        XCTAssertEqual(reload.profiles.count, 4)
        XCTAssertEqual(Set(reload.profiles.map { $0["id"].text }).count, 4)
    }
    @MainActor
    func testCSVAndTSVUseNativeParser() throws {
        let csv = "weight_lb,pa_ft,oat_c,ground_ft,total_ft,at_50ft_kias\n2300,0,15,520,1250,60\n"
        let rows = try NativeCSV.read(csv, phase: "landing")
        XCTAssertEqual(rows[0]["total_ft"].double, 1250)
        XCTAssertEqual(try NativeCSV.read(csv.replacingOccurrences(of: ",", with: "\t"), phase: "landing"), rows)
        XCTAssertEqual(try NativeCSV.read(String(decoding: NativeCSV.write(rows, phase: "landing"), as: UTF8.self), phase: "landing"), rows)
        XCTAssertThrowsError(try NativeCSV.read("wrong,header\n1,2", phase: "landing"))
        XCTAssertThrowsError(try NativeCSV.read(csv.replacingOccurrences(of: "520", with: "NaN"), phase: "landing"))
        let climb = try NativeEngine().data["builtin"]["climb"]
        XCTAssertEqual(try NativeCSV.read(String(decoding: NativeCSV.write(climb["rows"].array, phase: "climb"), as: UTF8.self), phase: "climb"), climb["rows"].array)
    }
    @MainActor
    func testLegacyDemoSelectionAndMissingClimbMigrateWithoutLosingProfiles() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let engine = try NativeEngine()
        var old = engine.data["profiles"][0]
        old["performance"]["climb"] = .null
        let saved = J.object(["version": .number(1), "profiles": .array([old]), "activeId": .string("demo")])
        try saved.encoded().write(to: directory.appendingPathComponent("native-aircraft-v1.json"))
        let store = NativeStore(directory: directory, engine: engine)
        XCTAssertEqual(store.activeID, old["id"].text)
        XCTAssertEqual(store.activeProfile?["performance"]["climb"]["mode"].text, "builtin")
        XCTAssertEqual(store.activeProfile?["wb"], old["wb"])
        var manual = try XCTUnwrap(store.activeProfile)
        manual["performance"]["climb"] = engine.data["builtin"]["climb"]
        try store.save(manual)
        let reloaded = NativeStore(directory: directory, engine: engine)
        XCTAssertEqual(reloaded.activeProfile?["performance"]["climb"]["rows"], manual["performance"]["climb"]["rows"])
        try store.importBackup(reloaded.backup())
        XCTAssertEqual(store.profiles.last?["performance"]["climb"]["rows"], manual["performance"]["climb"]["rows"])
        for id in store.profiles.map({ $0["id"].text }) { try store.delete(id) }
        XCTAssertNil(store.activeProfile); XCTAssertEqual(store.displayProfile, .null)
        manual["id"] = .string("")
        try store.save(manual)
        XCTAssertNotNil(store.activeProfile)
    }
}
