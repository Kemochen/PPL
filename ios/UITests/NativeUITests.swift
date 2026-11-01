import XCTest

final class NativeUITests: XCTestCase {
    func testNativePerformanceAndLandscape() throws {
        XCUIDevice.shared.orientation = .portrait
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.segmentedControls.firstMatch.waitForExistence(timeout: 20))
        saveScreenshot(app, "native-inputs")
        let calculate = app.buttons["calculate-performance"]
        for _ in 0..<6 where !calculate.isHittable { app.swipeUp() }
        XCTAssertTrue(calculate.isHittable)
        calculate.tap()
        let ground = app.descendants(matching: .any)["metric-ground_roll_ft"].firstMatch
        XCTAssertTrue(ground.waitForExistence(timeout: 10))
        XCTAssertTrue(ground.label.contains("1000.0"))
        saveScreenshot(app, "native-portrait")
        XCUIDevice.shared.orientation = .landscapeLeft
        let rotated = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in app.windows.firstMatch.frame.width > app.windows.firstMatch.frame.height }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [rotated], timeout: 10), .completed)
        Thread.sleep(forTimeInterval: 1)
        for _ in 0..<4 where !ground.exists { app.swipeUp() }
        XCTAssertTrue(ground.exists)
        saveScreenshot(app, "native-landscape")
        XCUIDevice.shared.orientation = .portrait
    }
    func testCruiseAndClimbControlsReachNativeEngine() throws {
        XCUIDevice.shared.orientation = .portrait
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.segmentedControls.firstMatch.waitForExistence(timeout: 20))
        app.segmentedControls.firstMatch.buttons["Cruise"].tap()
        calculatePerformance(app)
        XCTAssertTrue(app.descendants(matching: .any)["metric-GPH"].firstMatch.waitForExistence(timeout: 10))
        saveScreenshot(app, "native-cruise")
        for _ in 0..<8 where !app.segmentedControls.firstMatch.isHittable { app.swipeDown() }
        app.segmentedControls.firstMatch.buttons["Climb"].tap()
        calculatePerformance(app)
        let time = app.descendants(matching: .any)["metric-time_to_climb_min"].firstMatch
        XCTAssertTrue(time.waitForExistence(timeout: 10)); XCTAssertTrue(time.label.contains("11.7"))
        saveScreenshot(app, "native-climb")
    }
    private func calculatePerformance(_ app: XCUIApplication) {
        let button = app.buttons["calculate-performance"]
        for _ in 0..<8 where !button.isHittable { app.swipeUp() }
        XCTAssertTrue(button.isHittable); button.tap()
    }
    func testNativeWeightBalanceInterface() throws {
        XCUIDevice.shared.orientation = .portrait
        let app = XCUIApplication(); app.launch()
        let tab = app.tabBars.buttons["W&B"]
        XCTAssertTrue(tab.waitForExistence(timeout: 20)); tab.tap()
        let calculate = app.buttons["calculate-wb"]
        for _ in 0..<8 where !calculate.isHittable { app.swipeUp() }
        XCTAssertTrue(calculate.isHittable); calculate.tap()
        let envelope = app.descendants(matching: .any)["wb-phase-Ramp"].firstMatch
        XCTAssertTrue(envelope.waitForExistence(timeout: 10))
        saveScreenshot(app, "native-wb-phases")
        let plot = app.descendants(matching: .any)["cg-plot"].firstMatch
        for _ in 0..<3 where !plot.isHittable { app.swipeUp() }
        XCTAssertTrue(plot.exists)
        saveScreenshot(app, "native-wb-plot")
    }
    private func saveScreenshot(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot()); attachment.name = name; attachment.lifetime = .keepAlways
        add(attachment)
    }
}
