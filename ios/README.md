# PPL for iPhone / iPad

[Chinese AltStore build and installation guide](ALTSTORE.zh-CN.md)

## Status

This branch contains an iOS 26+ offline UIKit/WKWebView calculator. Ordinary
iPhones, Pro/Pro Max, landscape and expanded/resized windows are layout targets.
Scene-based lifecycle and safe-area constraints follow the actual window size,
without hardcoding a device model or speculative foldable dimensions.
The app bundles the existing Python calculation modules,
NumPy, a WebAssembly Python runtime and all UI assets. It needs no HTTPS server,
no local listening server and no first-launch download. The GitHub build produces
an unsigned device IPA for AltStore Classic to re-sign. GitHub Actions provides
Mac compilation and native-test verification; real AltStore installation and
specific folding hardware still require on-device acceptance testing.

The user clarified that older SE/iPhone 5 support is not required. iOS 25 and
earlier are not installation targets. Fold/unfold transitions are covered as
window-resize scenarios, not a claim of real-device certification for an
unverified model name or hardware configuration.

## Fully Local Runtime

`build_offline.py` creates the ignored `ios/BundledWeb/` resource folder at the project
root, avoiding nested-folder reference issues in XcodeGen. It renders the existing
UI at build time and bundles the unmodified
calculation modules with their runtime dependencies. The runtime archive has a
fixed SHA-512; NumPy and its dependencies are checked against the runtime lock's
SHA-256 values. Host `.so`/`.pyd` files are excluded; MarkupSafe uses its supported
pure-Python fallback. Licenses and source provenance are retained in the resources.
Build-time dependencies are pinned in `offline-requirements.txt`.

`OfflineAssets` serves only read-only app bundle resources through `ppl://offline`.
It does not bind a port. JavaScript calculator calls dispatch directly to the
existing Flask WSGI application in memory, using its test-client interface;
no Flask server is started. All input validation and POH restrictions are reused.
The app blocks external fetches and only opens explicitly tapped HTTPS source
links in the system browser. Those external documents are not offline downloads.

The runtime adds roughly 25 MB of uncompressed resources and needs a short local
initialization on launch. The minimum iOS target is 26.0, following the updated
device requirements; there is no SE-specific layout or simulator requirement.

Aircraft profiles persist on-device in the stable WKWebView origin. Safari and
the app do NOT share storage. Export JSON from the website and import it in the
app. JSON/CSV exports use native sharing (Save to Files), imports use the system
picker, and delete/reset confirmations are preserved. Back up before reinstalling.

## GitHub Build and AltStore Installation

The `.github/workflows/ios-build.yml` job uses a GitHub-hosted Mac.
Pushing iOS changes on `codex/ios-iphone-support` triggers it automatically.
Manual runs are also declared, but GitHub only exposes **Run workflow** after
the workflow exists on the repository's default branch. Its name is
**iOS IPA for AltStore**. Running it may consume
the repository's Actions allowance. Check the Actions run for the exact commit
before downloading its IPA; earlier artifacts can have different minimum iOS targets.

The workflow first runs Python/JavaScript checks, then builds an arm64 iPhoneOS
app on a Mac and runs the native simulator tests. Only successful runs publish
the **PPL-AltStore** artifact, containing:

- `PPL-AltStore.ipa`: unsigned device application, ready for AltStore re-signing.
- `PPL-AltStore.ipa.sha256`: checksum for download integrity.
- `package-info.json`: bundle identifier, version, minimum iOS and checksum.
- `INSTALL.txt`: short installation reminder.

The packager checks the Info.plist, executable, Mach-O architecture and device
platform, and ZIP CRC. An arm64 simulator build is rejected too. The bundle
identifier stays stable across updates; the build number uses the workflow run
number. No app extensions, special entitlements or JIT are needed.

1. Commit/push this branch with all project files, then open its Actions run.
2. After it succeeds, download **PPL-AltStore** from **Artifacts**.
3. Extract GitHub's outer ZIP; the file to import is `PPL-AltStore.ipa`, not the ZIP.
4. On the iPhone, open **AltStore Classic > My Apps > +** and select the IPA.
   Use your normal AltServer/Apple account setup to sign and install it.
5. Launch PPL. Wait for the bundled engine to initialize; no server setup is needed.

Use **AltStore Classic**, not AltStore PAL. AltStore handles signing on your side;
GitHub does not need Apple credentials, a paid developer membership, certificates
or provisioning profiles. You still need your own Apple account for AltStore.
Regular-account installations expire after seven days and need refreshing.
Keep the same account and bundle identifier for updates; export a JSON backup
before reinstalling or switching signing accounts.

This IPA cannot be installed directly by tapping it in Files, and is not a
TestFlight/App Store submission. Real AltStore installation still needs testing.
Never upload Apple passwords or signing keys into the repository or Actions secrets
for this unsigned workflow.

## Signed Device Build

On a Mac with Xcode and XcodeGen (`brew install xcodegen`):

```bash
cd ios
python3 -m pip install -r ../requirements.txt -r offline-requirements.txt
python3 build_offline.py
xcodegen generate
open PPL.xcodeproj
```

Select a unique bundle identifier and signing team in Xcode. A free Apple account
can provision limited personal-device testing from Xcode; it expires periodically.
TestFlight / App Store distribution requires a developer-program membership.
For an archive with an already configured account:

```bash
DEVELOPMENT_TEAM=YOUR_TEAM_ID BUNDLE_ID=your.owned.identifier bash build.sh archive
```

Open `build/PPL.xcarchive` in Xcode Organizer and export using the appropriate
distribution method and provisioning profile. An unsigned build is available
with `bash build.sh altstore` (`unsigned` is retained as an alias). Build outputs
and generated project files are ignored.

## Release Gates

- Run the native tests on a simulator and verify actual device install/signing.
- Verify first-ever launch and all calculations in airplane mode on a real device.
- Verify Files imports and JSON/CSV sharing on a real device, including cancellation.
- Check English/Chinese, keyboard, safe areas, Dynamic Type and landscape.
- Add final app icons, privacy policy, support information and distribution metadata.
- The old native server setting and UserDefaults access were removed. Audit the
  final app's storage and data handling before completing App Store privacy answers.
- Audit aircraft-data applicability and retain all third-party license notices.
- A web wrapper does not guarantee App Store acceptance. Review Apple's minimum
  functionality guideline before commercial distribution.

## Verification

`python ios/build_offline.py` prepares local resources and website parity cases.
`npm ci && npx playwright install chromium && npm run test:offline` tests a cold
start with browser networking disabled and every asset fulfilled from disk. It
compares all API fields/steps against the website, exercises all five calculator
UIs across phone, landscape and expanded-window sizes, checks that resizing
preserves results, saves a profile and reloads without losing data. `PPL_CHROME` and
`PPL_PLAYWRIGHT_PATH` may select an existing test browser/package on Windows.
The Mac workflow also tests actual bundled `WKURLSchemeHandler` startup and a
calculation in WebKit before publishing the IPA. Browser checks are not a
substitute for that native test or real AltStore installation.

CI pins Xcode 26.2 and the installed iOS 26.2 runtime, preferring Pro Max, then Pro.
It refuses to silently fall back to an older runtime. The earlier Xcode 16.4 /
iOS 18.5 test failure involved Apple's [WebKit overlay loading bug](https://bugs.webkit.org/show_bug.cgi?id=293831).
The new toolchain follows the user's iOS 26+ target rather than disabling tests
or retaining an older-device compatibility workaround.

References:
- https://faq.altstore.io/altstore-classic/your-altstore
- https://github.com/altstoreio/FAQ/blob/main/altstore-pal-v.-altstore-classic.md
- https://developer.apple.com/help/account/basics/about-your-developer-account
- https://developer.apple.com/app-store/review/guidelines/#minimum-functionality
