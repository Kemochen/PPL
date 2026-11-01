import UIKit
import WebKit

private final class ExportHandler: NSObject, WKScriptMessageHandler {
    weak var owner: CalculatorController?
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        owner?.exportFile(message)
    }
}

final class CalculatorController: UIViewController, WKNavigationDelegate, WKUIDelegate {
    private(set) var webView: WKWebView!
    private let status = UILabel()
    private let spinner = UIActivityIndicatorView(style: .medium)
    private let exportHandler = ExportHandler()

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "PPL Offline"
        view.backgroundColor = .systemBackground
        navigationItem.leftBarButtonItem = UIBarButtonItem(barButtonSystemItem: .refresh, target: self, action: #selector(reload))

        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        guard let resources = Bundle.main.url(forResource: "BundledWeb", withExtension: nil) else {
            let label = UILabel(frame: view.bounds)
            label.text = "Offline resources missing. Reinstall the full IPA."
            label.numberOfLines = 0
            label.textAlignment = .center
            view.addSubview(label)
            navigationItem.leftBarButtonItem?.isEnabled = false
            return
        }
        configuration.setURLSchemeHandler(OfflineAssets(root: resources), forURLScheme: "ppl")
        exportHandler.owner = self
        configuration.userContentController.add(exportHandler, name: "pplExport")
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(webView)

        status.numberOfLines = 0
        status.textAlignment = .center
        status.font = .preferredFont(forTextStyle: .body)
        status.adjustsFontForContentSizeCategory = true
        let stack = UIStackView(arrangedSubviews: [spinner, status])
        stack.axis = .vertical
        stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        let safe = view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: safe.topAnchor),
            webView.bottomAnchor.constraint(equalTo: safe.bottomAnchor),
            webView.leadingAnchor.constraint(equalTo: safe.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: safe.trailingAnchor),
            stack.centerYAnchor.constraint(equalTo: safe.centerYAnchor),
            stack.leadingAnchor.constraint(equalTo: safe.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: safe.trailingAnchor, constant: -24)
        ])
        reload()
    }

    @objc private func reload() {
        showStatus("Opening offline calculator / 正在打开离线计算器…")
        spinner.startAnimating()
        webView.load(URLRequest(url: OfflineOrigin.home))
    }

    private func showStatus(_ text: String) {
        spinner.stopAnimating()
        status.text = text
        status.isHidden = false
        webView.isHidden = true
    }

    private func notice(_ text: String) {
        let alert = UIAlertController(title: "PPL", message: text, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        present(alert, animated: true)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        spinner.stopAnimating()
        status.isHidden = true
        webView.isHidden = false
    }

    private func failed(_ error: Error) {
        if (error as NSError).code == NSURLErrorCancelled { return }
        showStatus("Unable to open bundled calculator. Tap Refresh or reinstall the complete IPA.\n\n无法打开本地计算器。请刷新或安装完整 IPA。\n\n" + error.localizedDescription)
    }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { failed(error) }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { failed(error) }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) { showStatus("Page stopped. Tap Refresh.\n页面已停止，请刷新。") }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if OfflineOrigin.contains(url) {
            if action.targetFrame == nil { webView.load(action.request); decisionHandler(.cancel) }
            else { decisionHandler(.allow) }
        } else {
            decisionHandler(.cancel)
            if action.navigationType == .linkActivated && url.scheme == "https" { UIApplication.shared.open(url) }
        }
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let alert = UIAlertController(title: "PPL", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler() })
        present(alert, animated: true)
    }
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = UIAlertController(title: "PPL", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Cancel / 取消", style: .cancel) { _ in completionHandler(false) })
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler(true) })
        present(alert, animated: true)
    }

    fileprivate func exportFile(_ message: WKScriptMessage) {
        guard message.frameInfo.isMainFrame,
              let frameURL = message.frameInfo.request.url, OfflineOrigin.contains(frameURL),
              let body = message.body as? [String: String],
              let content = body["content"], content.utf8.count <= 5_000_000,
              let rawName = body["filename"] else { return }
        let filename = (rawName as NSString).lastPathComponent
        guard ["json", "csv"].contains((filename as NSString).pathExtension.lowercased()) else { return }
        do {
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: nil)
            let url = directory.appendingPathComponent(filename)
            try Data(content.utf8).write(to: url, options: .atomic)
            let share = UIActivityViewController(activityItems: [url], applicationActivities: nil)
            share.popoverPresentationController?.barButtonItem = navigationItem.leftBarButtonItem
            share.completionWithItemsHandler = { _, _, _, _ in try? FileManager.default.removeItem(at: directory) }
            present(share, animated: true)
        } catch { notice(error.localizedDescription) }
    }
}
