# Native Swift PPL

Branch: `codex/swift-native`. Deployment target: iOS 26+.

## App Architecture

- SwiftUI forms, tabs, file import/export, POH tables, calculation steps and CG plot.
- Foundation/Swift calculation engine: no WebView, Python, JavaScript or WebAssembly.
- Native JSON persistence in `Documents/native-aircraft-v1.json`, written atomically.
- Apple TabularData parses CSV/TSV files. Aircraft backups retain the website's
  version-1 JSON format; full-precision moments and table values are preserved.
- Native data validation keeps drafts separate from calculable W&B / POH tables.
- C172N built-in data and the explicitly labelled 1974 C172M reference remain
  separate. No missing FFCT empty weight/moment is copied from GFJE.

The existing website remains a separate Python application. At build time,
`export_native_data.py` copies its POH numbers and model catalogue into the
74 KB `Resources/NativeData.json`, and generates reference test cases. Python is
only a build/test tool and is not included in the IPA. Do not manually change
the generated POH file without updating its source and verification cases.

## Migration From the Previous App

Before updating the WebView-based app, export your aircraft backup JSON.
The native app cannot automatically read WebView localStorage. Open Aircraft,
import that JSON using the download icon, then select the imported aircraft.
Keep the original backup until you have checked W&B, arms, tank capacity and POH
correction rules. Reinstallation/deletion or changing the AltStore account can
affect app data, so back up first.

## Build / Install

Push this branch to GitHub. **Native Swift IPA for AltStore** runs the website
regression tests, exports data, compiles the native app, checks numerical parity,
and runs native UI tests on iOS 26.2 / Pro Max. Passing builds publish the
**PPL-AltStore** artifact. Extract its ZIP and import `PPL-AltStore.ipa` into
AltStore Classic, which performs signing. Do not put Apple credentials in CI.

On a Mac with Xcode 26.2 and XcodeGen:

```bash
python3 -m pip install -r requirements.txt -r ios/offline-requirements.txt
bash ios/build.sh altstore
```

For local editing, run `python3 ios/export_native_data.py`, then
`cd ios && xcodegen generate && open PPL.xcodeproj`.

The IPA verifier rejects a native build that lacks its POH data or contains
Python files, wheels, WASM, HTML or JavaScript. UIKit/SwiftUI system frameworks
are supplied by iOS. The native branch no longer uses `build_offline.py` or
`BundledWeb`; those legacy development tools/tests are retained for reference.

## Verification and Limits

- 77 initial numerical parity cases cover interpolation, bounds, wind reference,
  grass corrections, FFCT restrictions, manual tables, climb and W&B.
- Native persistence and CSV/TSV round-trip tests protect backup compatibility.
- Native UI tests capture portrait/landscape screenshots in the test artifacts.
- SwiftUI uses actual scene/window size; no speculative foldable dimensions are
  hardcoded. Specific folding hardware and AltStore installation require device QA.
- This remains a POH study/calculation tool. Verify against the aircraft's actual
  approved POH, configuration and current weighing records before operational use.

App icons, final privacy/support information and commercial-release review remain
separate release tasks. Native implementation does not imply App Store approval.
