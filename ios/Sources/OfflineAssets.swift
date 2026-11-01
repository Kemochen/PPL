import Foundation
import WebKit

enum OfflineOrigin {
    static let home = URL(string: "ppl://offline/index.html")!
    static func contains(_ url: URL) -> Bool {
        url.scheme?.lowercased() == "ppl" && url.host?.lowercased() == "offline"
            && url.port == nil && url.user == nil && url.password == nil
    }

    static func resource(_ url: URL, root: URL) -> URL? {
        guard contains(url) else { return nil }
        let path = url.path.isEmpty || url.path == "/" ? "/index.html" : url.path
        let file = root.appendingPathComponent(String(path.dropFirst())).standardizedFileURL.resolvingSymlinksInPath()
        let base = root.standardizedFileURL.resolvingSymlinksInPath().path + "/"
        return file.path.hasPrefix(base) ? file : nil
    }
}

final class OfflineAssets: NSObject, WKURLSchemeHandler {
    private let root: URL
    init(root: URL) { self.root = root }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url, task.request.httpMethod == "GET",
              let file = OfflineOrigin.resource(url, root: root) else {
            task.didFailWithError(URLError(.noPermissionsToReadFile)); return
        }
        do {
            let data = try Data(contentsOf: file)
            let types = ["html": "text/html; charset=utf-8", "js": "text/javascript; charset=utf-8",
                         "css": "text/css; charset=utf-8", "json": "application/json",
                         "wasm": "application/wasm", "zip": "application/zip", "whl": "application/zip"]
            let headers = ["Content-Type": types[file.pathExtension] ?? "application/octet-stream",
                           "Content-Length": String(data.count), "Access-Control-Allow-Origin": "*",
                           "Content-Security-Policy": "default-src 'self' ppl:; script-src 'self' ppl: 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; connect-src ppl:; img-src 'self' data:; worker-src 'none'; object-src 'none'"]
            let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers)!
            task.didReceive(response)
            task.didReceive(data)
            task.didFinish()
        } catch { task.didFailWithError(error) }
    }
    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}
}
