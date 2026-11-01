import XCTest

final class NativeUITests: XCTestCase {
    func testNativePerformanceAndLandscape() throws {
        let app = XCUIApplication(); app.launch()
        let calculate = app.buttons["calculate-performance"]
        XCTAssertTrue(calculate.waitForExistence(timeout: 20))
        for _ in 0..<6 where !calculate.isHittable { app.swipeUp() }
        calculate.tap()
        let ground = app.staticTexts["metric-ground_roll_ft"]
        XCTAssertTrue(ground.waitForExistence(timeout: 10))
        XCTAssertTrue(ground.label.contains("1000.0"))
        saveScreenshot(app, "native-portrait")
        XCUIDevice.shared.orientation = .landscapeLeft
        for _ in 0..<4 where !ground.exists { app.swipeUp() }
        XCTAssertTrue(ground.exists)
        saveScreenshot(app, "native-landscape")
        XCUIDevice.shared.orientation = .portrait
    }
    private func saveScreenshot(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot()); attachment.name = name; attachment.lifetime = .keepAlways
        add(attachment)
    }
}
