# PPL

## iOS Branch

The current native rewrite is `codex/swift-native`: **SwiftUI interface and Swift
calculations**, with no WebView/Python/WASM in the IPA. See [native app guide](ios/NATIVE.md).
Export a JSON backup before replacing the older WebView app; native storage does
not automatically import WebView localStorage. Its GitHub workflow is
**Native Swift IPA for AltStore**.

The following notes describe the earlier `codex/ios-iphone-support` build:

The `codex/ios-iphone-support` branch adds an iOS 26+ offline calculator with
adaptive layouts for ordinary iPhones, Pro/Pro Max, landscape and expanded windows.
See [iOS setup and build status](ios/README.md). Python,
NumPy, calculation tables and UI assets are bundled in the IPA. There is no
server, HTTPS configuration or first-launch network download. The Mac CI workflow
builds **PPL-AltStore.ipa** for **AltStore Classic** to re-sign and install with your
own Apple account. No Apple signing secrets or paid membership are needed by CI.
The device bundle, Mach-O architecture and ZIP are checked before packaging.
Offline cold-start, persistence and website-parity browser checks are included.
Check the corresponding Actions run for Mac build/native-test results. Actual
AltStore installation and specific folding hardware still need device validation.
Pushing iOS changes on this branch triggers the Mac build; manual runs also
require the workflow file to be registered on the repository's default branch.

中文安装说明：[GitHub 打包与 AltStore 安装](ios/ALTSTORE.zh-CN.md)。

C172N performance calculator with takeoff, landing, cruise, climb, aircraft profiles,
and weight-and-balance calculations.

## Aircraft Profiles

Use the Aircraft tab to save, edit, duplicate, and select tail-specific profiles.
Profiles are stored in this browser, not on the server. Export/import a JSON backup
to transfer them between devices. The initial C-GFJE profile is C172N, serial
17272818, 1979. The user confirmed that the existing 1541 lb / 38.2 in W&B data
belongs to GFJE. The profile restores those values and Baggage 2 at 123 in.
Usable fuel initially uses the standard 40 US gal configuration and is editable.
Previously created blank GFJE profiles are filled without replacing user edits.

Basic empty weight, empty moment, station arms and station availability are
managed in Aircraft. W&B displays those fixed values as read-only and accepts
passenger/baggage weights and fuel quantities for the current calculation.
Saving changes in Aircraft updates W&B automatically. The saved full-precision
empty moment is used for calculations even though displayed values use one decimal.

The catalogue includes C150M, C152, C172L/M/N/P/R/S, C182T, PA-28-140/161/181,
DA20-C1, DA40 XLT, DA40 NG, and a custom model. Some C172 normal-category landplane
reference limits are prefilled. Other entries require manual POH/W&B data. A
catalogue entry does not imply a matching takeoff, landing, cruise, or climb
dataset. Built-in performance data is C172N only. Takeoff, landing and cruise can
also use manually entered, tail-specific POH tables. Climb remains C172N only.
Demo mode retains the existing C172N training example. A separate, explicitly
labelled 1974 C172M/Skyhawk reference is available for the C-FFCT preset.

### C-FFCT Reference Profile

C-FFCT is listed as Cessna 172M, serial 17262961, manufactured in 1974. Operator
fleet information confirms the model; the registration mirror reports a CCAR
snapshot dated 2026-06-30. The preset is added once to existing browser storage
without replacing profiles or switching the active aircraft. User-entered FFCT
profiles are retained rather than overwritten, and deleted presets stay deleted.
Its actual empty weight, moment, ramp limit and tank option are unknown and stay
blank. No GFJE empty-aircraft values are copied.

The 1974 performance reference uses the original manufacturer's Owner's Manual
scanned for N9850V and linked by Air America Flight Center, printed pages 6-1
through 6-5 (PDF pages 63-67). It is **not a verified FFCT-specific manual**.
The key takeoff cells were cross-checked against a 1974 excerpt archived by NTSB.
The AAFC scan remains the recorded data source. Check actual aircraft
propeller, configuration, approved manual and STCs before treating it as applicable.

- Takeoff: weights 1700/2000/2300 lb, PA 0/2500/5000/7500 ft, headwind 0/10/20 kt.
  Interpolate altitude and headwind; apply +10% per 25 F above standard temperature.
  Dry grass adds 7% of the corrected **total over-50-ft distance to both distances**.
- Landing: 2300 lb reference, PA 0-7500 ft, standard-day OAT only, flaps 40,
  power off, approach IAS 70 MPH. Headwind reduces both distances 10% per 5 kt.
  Dry grass adds 20% of the corrected **total over-50-ft distance to both distances**.
- Cruise: Skyhawk configuration, 2300 lb, standard-day OAT, lean mixture,
  McCauley 1C160/DTM7553 or CTM7553. Interpolate RPM and altitude in the original
  MPH units, then convert TAS to KTAS. Results above normal 75% cruise power are
  rejected. The manual notes standard Model 172 speeds are 1-3 MPH below Skyhawk.
- No tailwind rule or nonstandard-temperature landing/cruise correction is inferred.
  Climb remains unavailable for C-FFCT. MPH-to-knot conversion uses exact unit lengths.

Sources:

- [Operator: C-FFCT is a C172M](https://compassflying.com/fleet/)
- [Registration mirror: identity, serial and manufacture year](https://www.regosearch.com/aircraft/ca/FFCT)
- [1974 Owner's Manual, AAFC N9850V scan](https://airamericafc.com/wp-content/uploads/2024/03/N9850V-C172M-OM-1974.pdf)
- [NTSB's 1974 excerpt](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=.PDF&FileName=Cessna+172M+Owners+Manual+Excerpts-Master.PDF&ID=40326596)

Profiles use lb, inches, full lb-in moments (not moment/1000), and US gallons.
Fuel density, seat position arms, tank capacity, baggage limits and the CG
envelope are editable. Calculations retain full precision and display one decimal.
Incomplete profiles can be saved as drafts but cannot calculate W&B.
The W&B calculation model assumes fixed loading-station arms and a single fuel
arm. Variable fuel arms or separately loaded tanks require a matching loading
model rather than entering an arbitrary average arm.

## Manual POH Performance Tables

In Aircraft, open POH performance data and select Takeoff, Landing or Cruise.
Each phase has its own source mode: Not loaded, Built-in C172N, Manual POH, or
the labelled 1974 C172M reference for matching model/year profiles.
Record the POH edition/revision, figure/page and configuration/conditions. Enter
rows directly, paste CSV/Excel TSV, or import a CSV/TSV file. CSV template exports
the required header; Export CSV downloads the current numeric table. Imports
replace rows only after confirmation and do not change them on parsing failure.
Save aircraft to persist all three tables with the profile and include them in
JSON backups. Draft tables can be saved; only complete tables enable calculation.
An incomplete manual override never silently falls back to built-in C172N data.

Headers (units are lb, ft, Celsius, KIAS/KTAS and US gal/h):

```csv
weight_lb,pa_ft,oat_c,ground_ft,total_ft,lift_off_kias,at_50ft_kias
```

```csv
weight_lb,pa_ft,oat_c,ground_ft,total_ft,at_50ft_kias
```

```csv
pa_ft,isa_offset_c,rpm,percent_bhp,ktas,gph
```

Takeoff/landing require a complete PA/OAT grid at each recorded weight. Actual
weight uses the next table weight not below it, with no interpolation across
weight tables. Each axis may have one value for exact lookups. Cruise records a
single reference weight and interpolates RPM, ISA offset and pressure altitude.
The entered OAT bracket is interpolated to altitude, then converted to ISA offset
using the existing 15 C minus 2 C/1000 ft convention. Unsupported coordinates and
RPM ranges are rejected rather than extrapolated.

Wind rules use percentage per knot step, with an optional limit if the POH gives
one. Blank rules are unsupported, not assumed to be C172N rules. Grass correction
can add a percentage of wind-corrected ground roll to both distances or increase
each corrected distance by its own percentage. Unsupported wind/grass conditions
return an error. All results include source, conditions and interpolation steps.
This editor handles numeric tables, not automatic digitization of POH graphs or
arbitrary chart-specific correction methods.

Sources:

- [Operator fleet: C-GFJE is a C172N](https://compassflying.com/fleet/)
- [CCAR mirror: C-GFJE, serial and manufacture year](https://www.regosearch.com/aircraft/ca/GFJE)
- [FAA TCDS 3A12, archived Rev. 74: C172 model years and reference limits](https://aerovalley.org/wp-content/uploads/2023/07/Cessna_type_cert.pdf)
- [Hartzell approved-model serial/year table](https://hartzellprop.com/wp-content/uploads/SA03300CHINST-Rev-1-signed.pdf)

The Canadian official register was inaccessible during this research. The mirror
reports a CCAR snapshot dated 2026-01-20. Identity, configuration and applicable
limits should be checked against the aircraft's own documents, including STCs.

## Tests

```bash
python -m unittest test_reference_1974 test_performance test_aircraft test_wind -v
```

## Run Locally

```bash
pip install -r requirements.txt
flask --app app run --host=0.0.0.0 --port=5000
```

Open:

```text
http://127.0.0.1:5000
```

## Synology Container Manager

Use Container Manager with the included `docker-compose.yml`.

The container uses the latest official Python image and maps:

```text
NAS port 8088 -> container port 5000
```

After starting the project, open:

```text
http://YOUR_NAS_IP:8088
```

For a DSM reverse proxy or custom domain, point it to:

```text
http://127.0.0.1:8088
```
