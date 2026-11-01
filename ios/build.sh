#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" != Darwin ]]; then
  echo "iOS builds require macOS and Xcode. Use the manual GitHub Actions workflow from Windows." >&2
  exit 1
fi
command -v xcodegen >/dev/null || { echo "Install XcodeGen: brew install xcodegen" >&2; exit 1; }
xcodebuild -version
python3 build_offline.py
xcodegen generate
mode="${1:-altstore}"
case "$mode" in
  altstore|unsigned)
    xcodebuild -project PPL.xcodeproj -scheme PPL -configuration Release \
      -destination 'generic/platform=iOS' -derivedDataPath build/DerivedData \
      ARCHS=arm64 ONLY_ACTIVE_ARCH=NO CODE_SIGNING_ALLOWED=NO \
      CURRENT_PROJECT_VERSION="${GITHUB_RUN_NUMBER:-1}" build
    python3 package_ipa.py build/DerivedData/Build/Products/Release-iphoneos/PPL.app \
      build/PPL-AltStore.ipa | tee build/package-info.json
    echo "Install PPL-AltStore.ipa through AltStore Classic, which re-signs it with your Apple account." \
      | tee build/INSTALL.txt
    ;;
  archive)
    : "${DEVELOPMENT_TEAM:?Set DEVELOPMENT_TEAM to your Apple team ID}"
    : "${BUNDLE_ID:?Set BUNDLE_ID to your registered bundle identifier}"
    xcodebuild -project PPL.xcodeproj -scheme PPL -configuration Release \
      -destination 'generic/platform=iOS' -archivePath build/PPL.xcarchive \
      DEVELOPMENT_TEAM="$DEVELOPMENT_TEAM" PRODUCT_BUNDLE_IDENTIFIER="$BUNDLE_ID" \
      -allowProvisioningUpdates archive
    echo "Open build/PPL.xcarchive in Xcode Organizer to export with your provisioning profile."
    ;;
  *) echo "Usage: bash build.sh [altstore|archive]" >&2; exit 2 ;;
esac
