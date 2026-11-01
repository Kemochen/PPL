import XCTest
import UIKit
import WebKit
@testable import PPL

final class OfflineTests: XCTestCase {
    func testOnlyBundledOriginIsAllowed() {
        XCTAssertTrue(OfflineOrigin.contains(OfflineOrigin.home))
        for text in ["https://offline/index.html", "http://127.0.0.1", "ppl://other/index.html", "ppl://user@offline/index.html", "ppl://offline:123/index.html"] {
            XCTAssertFalse(OfflineOrigin.contains(URL(string: text)!))
        }
    }

    func testResourceTraversalIsRejected() {
        let root = URL(fileURLWithPath: "/bundle/Offline", isDirectory: true)
        XCTAssertEqual(OfflineOrigin.resource(OfflineOrigin.home, root: root)?.lastPathComponent, "index.html")
        XCTAssertNil(OfflineOrigin.resource(URL(string: "ppl://offline/../../outside")!, root: root))
    }

    @MainActor
    private func javascript(_ text: String, webView: WKWebView) async throws -> Any? {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Any?, Error>) in
            webView.evaluateJavaScript(text) { value, error in
                if let error = error { continuation.resume(throwing: error) }
                else { continuation.resume(returning: value) }
            }
        }
    }

    @MainActor
    func testBundledWebKitStartsAndCalculatesWithoutServer() async throws {
        var hostWindow: UIWindow?
        for _ in 0..<100 {
            hostWindow = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
                .flatMap { $0.windows }.first { $0.isKeyWindow }
            if hostWindow != nil { break }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        let nav = try XCTUnwrap(hostWindow?.rootViewController as? UINavigationController)
        let controller = try XCTUnwrap(nav.viewControllers.first as? CalculatorController)
        controller.loadViewIfNeeded()
        let webView = try XCTUnwrap(controller.webView)
        var started = false
        for _ in 0..<600 {
            if (try? await javascript("typeof window.pplOfflineReady !== 'undefined'", webView: webView)) as? Bool == true {
                started = true; break
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        XCTAssertTrue(started, "Bundled startup script did not load")
        guard started else { return }
        let complete = expectation(description: "Local Python engine and all parity cases")
        webView.callAsyncJavaScript("""
            await window.pplOfflineReady;
            const rows = await (await fetch('/api/aircraft/models')).json();
            const body = new FormData();
            body.set('weight_lbs', '2300');
            body.set('pressure_altitude_ft', '2000');
            body.set('oat_c', '20');
            const takeoff = await (await fetch('/api/takeoff', {method:'POST', body})).json();
            return {ready: document.documentElement.dataset.offlineReady,
                    count: rows.starter_profiles.length, ground: takeoff.result.ground_roll_ft};
            """, arguments: [:], in: nil, in: .page) { result in
                switch result {
                case .success(let value):
                    let values = value as? [String: Any]
                    XCTAssertEqual(values?["ready"] as? String, "true")
                    XCTAssertEqual(values?["count"] as? Int, 2)
                    XCTAssertEqual(values?["ground"] as? Double, 1000)
                case .failure(let error): XCTFail("Offline WebKit error: \(error)")
                }
                complete.fulfill()
            }
        await fulfillment(of: [complete], timeout: 120)
    }
}
