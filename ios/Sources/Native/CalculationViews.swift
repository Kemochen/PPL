import SwiftUI
import UIKit

@MainActor
func endNativeEditing() {
    UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
}

func fieldName(_ key: String, chinese: Bool = false) -> String {
    let labels: [String: (String, String)] = [
        "weight_lbs": ("Weight", "重量"), "pressure_altitude_ft": ("Pressure altitude", "压力高度"), "oat_c": ("Outside air temperature", "外界温度"),
        "rpm": ("RPM", "转速"), "target_altitude_ft": ("Target altitude", "目标高度"), "runway_heading_deg": ("Runway", "跑道"),
        "wind_direction_deg": ("Wind direction", "风向"), "wind_speed_kt": ("Wind speed", "风速"), "magnetic_variation_deg": ("Airport magnetic variation", "机场磁差"),
        "lower_oat_altitude_ft": ("Lower OAT altitude", "低端温度高度"), "upper_oat_altitude_ft": ("Upper OAT altitude", "高端温度高度"),
        "lower_oat_c": ("Lower altitude OAT", "低端温度"), "upper_oat_c": ("Upper altitude OAT", "高端温度"),
        "ground_roll_ft": ("Ground roll", "地面滑跑"), "total_clear_50ft_ft": ("Over 50 ft", "越过 50 ft"), "total_to_clear_50ft_ft": ("Over 50 ft", "越过 50 ft"),
        "input_weight_lbs": ("Input weight", "输入重量"), "selected_table_lbs": ("Selected POH weight", "采用的 POH 重量表"),
        "Pressure altitude ft": ("Pressure altitude", "压力高度"), "OAT at altitude C": ("Interpolated OAT", "插值得到的温度"),
        "ISA temp at altitude C": ("ISA temperature", "标准温度"), "Temp offset from ISA C": ("ISA offset", "标准温差"),
        "headwind_component_kt": ("Headwind", "逆风分量"), "tailwind_component_kt": ("Tailwind", "顺风分量"), "crosswind_component_kt": ("Crosswind", "侧风分量"),
        "lift_off_kias": ("Lift-off speed", "离地速度"), "at_50ft_kias": ("Speed at 50 ft", "50 ft 速度"), "approach_kias": ("Approach speed", "进近速度"),
        "Percent BHP": ("Power", "功率"), "KTAS": ("True airspeed", "真空速"), "GPH": ("Fuel flow", "耗油率"),
        "time_to_climb_min": ("Climb time", "爬升时间"), "distance_to_climb_nm": ("Climb distance", "爬升距离"),
        "fuel_used_gal_climb_only": ("Climb fuel", "爬升用油"), "fuel_used_gal_with_start_taxi_takeoff": ("Fuel incl. start / taxi / takeoff", "含启动、滑行和起飞用油"),
        "pressure_alt_ft": ("Initial pressure altitude", "起始压力高度"), "target_alt_ft": ("Target altitude", "目标高度"),
        "standard_oat_at_pressure_alt_c": ("ISA at start", "起始标准温度"),
        "climb_speed_kias_at_start": ("Initial climb speed", "起始爬升速度"), "climb_speed_kias_at_target": ("Target climb speed", "目标高度爬升速度"),
        "rate_of_climb_fpm_at_start": ("Initial climb rate", "起始爬升率"), "rate_of_climb_fpm_at_target": ("Target climb rate", "目标高度爬升率"),
        "pa_ft": ("Pressure altitude", "压力高度"), "std_temp_c": ("Standard temperature", "标准温度"),
        "climb_speed_kias": ("Climb speed", "爬升速度"), "rate_fpm": ("Climb rate", "爬升率"),
        "time_from_sl_min": ("Cumulative time from sea level", "从海平面累计时间"), "fuel_from_sl_gal": ("Cumulative fuel from sea level", "从海平面累计用油"),
        "distance_from_sl_nm": ("Cumulative distance from sea level", "从海平面累计距离"),
        "empty_weight_lb": ("Basic empty weight", "基本空重"), "empty_moment_lb_in": ("Empty moment (full lb-in)", "空机力矩（完整 lb-in）"),
        "fuel_density_lb_gal": ("Fuel density", "燃油密度"), "fuel_arm_in": ("Fuel arm", "燃油力臂"), "usable_fuel_gal": ("Usable fuel", "可用燃油"),
        "max_ramp_lb": ("Maximum ramp weight", "最大停机重量"), "max_takeoff_lb": ("Maximum takeoff weight", "最大起飞重量"),
        "max_landing_lb": ("Maximum landing weight", "最大降落重量"), "baggage_total_lb": ("Combined baggage limit", "行李总重量限制")]
    if let label = labels[key] { return chinese ? label.1 : label.0 }
    return key.replacingOccurrences(of: "_", with: " ")
}

func unitFor(_ key: String) -> String {
    if key == "KTAS" { return "kt" }
    if key == "GPH" { return "US gal/h" }
    if key == "Percent BHP" { return "%" }
    if key.contains("kias") { return "KIAS" }
    if key.hasSuffix("_kt") { return "kt" }
    if key.hasSuffix("_fpm") || key.contains("rate_of_climb") { return "ft/min" }
    if key.hasSuffix("_min") { return "min" }
    if key.hasSuffix("_nm") { return "NM" }
    if key.contains("fuel_used") || key.hasSuffix("_gal") { return "US gal" }
    if key.hasSuffix("_ft") || key.hasSuffix(" ft") { return "ft" }
    if key.hasSuffix("_c") || key.hasSuffix(" C") { return "°C" }
    if key.contains("lbs") || key.hasSuffix("_lb") { return "lb" }
    return ""
}

struct NumberRow: View {
    var title: String
    var unit: String = ""
    var id: String = ""
    @Binding var text: String
    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title).fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 12)
            TextField("—", text: $text).keyboardType(.numbersAndPunctuation)
                .multilineTextAlignment(.trailing).monospacedDigit().frame(width: 105)
                .accessibilityLabel(title).accessibilityIdentifier(id)
            if !unit.isEmpty { Text(unit).font(.caption).foregroundStyle(.secondary).frame(minWidth: 25, alignment: .leading) }
        }
    }
}

@MainActor
struct AircraftSelection: View {
    @EnvironmentObject var store: NativeStore
    var body: some View {
        Picker(store.label("Aircraft", "飞机"), selection: Binding(get: { store.activeID }, set: { store.select($0) })) {
            if store.profiles.isEmpty { Text(store.label("No aircraft", "暂无飞机")).tag("") }
            ForEach(Array(store.profiles.enumerated()), id: \.offset) { _, profile in
                Text(profile["registration"].text + " / " + profile["name"].text).tag(profile["id"].text)
            }
        }
    }
}

@MainActor
struct NativeRootView: View {
    @StateObject private var store = NativeStore()
    var body: some View {
        Group {
            if let error = store.startupError {
                ContentUnavailableView("PPL", systemImage: "exclamationmark.triangle", description: Text(error))
            } else {
                TabView {
                    Tab(store.label("Performance", "性能"), systemImage: "airplane.departure") { NavigationStack { PerformanceView() } }
                    Tab("W&B", systemImage: "scalemass") { NavigationStack { WeightBalanceView() } }
                    Tab(store.label("Aircraft", "飞机档案"), systemImage: "airplane") { NavigationStack { AircraftListView() } }
                }.tabViewStyle(.sidebarAdaptable)
            }
        }
        .environmentObject(store)
        .alert("PPL", isPresented: Binding(get: { store.errorMessage != nil }, set: { if !$0 { store.errorMessage = nil } })) {
            Button("OK") { store.errorMessage = nil }
        } message: { Text(store.errorMessage ?? "") }
    }
}

@MainActor
struct PerformanceView: View {
    @EnvironmentObject var store: NativeStore
    @State private var phase = Phase.takeoff
    @State private var inputs: [Phase: [String: String]] = Dictionary(uniqueKeysWithValues: Phase.allCases.map { phase in
        (phase, ["weight_lbs": "2300", "pressure_altitude_ft": phase == .cruise ? "8500" : phase == .climb ? "500" : "2000",
                 "oat_c": phase == .climb ? "25" : "20", "rpm": "2400", "target_altitude_ft": "6500",
                 "lower_oat_altitude_ft": "6000", "lower_oat_c": "8", "upper_oat_altitude_ft": "9000", "upper_oat_c": "2",
                 "wind_reference": "true", "variation_direction": "east", "grass": ""])
    })
    @State private var calculation: Calculation?
    @State private var error: String?
    @State private var resultToken = UUID()
    @FocusState private var keyboard: Bool

    private var mode: String { store.activeProfile?["performance"][phase.rawValue]["mode"].text ?? "builtin" }
    private func binding(_ key: String) -> Binding<String> {
        Binding(get: { inputs[phase]?[key] ?? "" }, set: { inputs[phase, default: [:]][key] = $0; calculation = nil; error = nil })
    }
    private func row(_ key: String, _ unit: String) -> some View {
        NumberRow(title: fieldName(key, chinese: store.chinese), unit: unit, id: key, text: binding(key)).focused($keyboard)
    }
    var body: some View {
        ScrollViewReader { proxy in
            Form {
                Section { AircraftSelection() }
                if mode == "c172m1974" {
                    Section { Text(store.engine?.data["reference"][phase.rawValue]["conditions"].text ?? "1974 reference only; verify applicability to this aircraft.").font(.caption).foregroundStyle(.orange) }
                }
                Section {
                    Picker(store.label("Calculation", "计算"), selection: $phase) {
                        Text(store.label("Takeoff", "起飞")).tag(Phase.takeoff)
                        Text(store.label("Landing", "降落")).tag(Phase.landing)
                        Text(store.label("Cruise", "巡航")).tag(Phase.cruise)
                        Text(store.label("Climb", "爬升")).tag(Phase.climb)
                    }.pickerStyle(.segmented).accessibilityIdentifier("phase-picker")
                    if phase == .takeoff || (phase == .landing && mode != "builtin") { row("weight_lbs", "lb") }
                    row("pressure_altitude_ft", "ft")
                    if phase == .cruise {
                        row("rpm", "RPM")
                        row("lower_oat_altitude_ft", "ft"); row("lower_oat_c", "°C")
                        row("upper_oat_altitude_ft", "ft"); row("upper_oat_c", "°C")
                    } else {
                        if phase == .climb { row("target_altitude_ft", "ft") }
                        row("oat_c", "°C")
                    }
                }
                if phase == .takeoff || phase == .landing { windSection }
                Section {
                    Button {
                        keyboard = false; endNativeEditing()
                        do {
                            guard let engine = store.engine else { return }
                            calculation = try engine.calculate(phase.rawValue, form: .object((inputs[phase] ?? [:]).mapValues(J.string)), profile: store.activeProfile)
                            error = nil; resultToken = UUID()
                        } catch { self.error = error.localizedDescription; calculation = nil }
                    } label: { Label(store.label("Calculate", "计算"), systemImage: "equal.square") }
                    .accessibilityIdentifier("calculate-performance")
                    .disabled(store.activeProfile == nil)
                    .id("calculate-anchor")
                }
                if let error { Section { Text(error).foregroundStyle(.red).accessibilityIdentifier("calculation-error") } }
                if let calculation {
                    MetricSection(calculation: calculation)
                    StepsSection(steps: calculation.steps)
                }
            }
            .onChange(of: resultToken) { _, _ in
                Task { @MainActor in
                    try? await Task.sleep(for: .milliseconds(150))
                    withAnimation { proxy.scrollTo("calculate-anchor", anchor: .top) }
                }
            }
        }
        .navigationTitle(store.label(phase.title, ["takeoff": "起飞", "landing": "降落", "cruise": "巡航", "climb": "爬升"][phase.rawValue]!))
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) { Button(store.chinese ? "EN" : "中文") { store.toggleLanguage() } }
            ToolbarItemGroup(placement: .keyboard) { Spacer(); Button(store.label("Done", "完成")) { keyboard = false; endNativeEditing() } }
        }
        .onChange(of: phase) { _, _ in calculation = nil; error = nil }
        .onChange(of: store.activeID) { _, _ in calculation = nil; error = nil }
        .onChange(of: store.activeProfile) { _, _ in calculation = nil; error = nil }
    }
    private var windSection: some View {
        Section(store.label("Wind and surface", "风与道面")) {
            row("runway_heading_deg", "RWY"); row("wind_direction_deg", "°"); row("wind_speed_kt", "kt")
            Picker(store.label("Wind reference", "风向基准"), selection: binding("wind_reference")) {
                Text(store.label("True (METAR)", "真北（METAR）")).tag("true")
                Text(store.label("Magnetic", "磁北")).tag("magnetic")
            }
            if binding("wind_reference").wrappedValue == "true" {
                row("magnetic_variation_deg", "°")
                Picker(store.label("Variation", "磁差方向"), selection: binding("variation_direction")) {
                    Text(store.label("East", "东")).tag("east"); Text(store.label("West", "西")).tag("west")
                }.pickerStyle(.segmented)
            }
            Toggle(store.label("Dry grass", "干草地"), isOn: Binding(get: { binding("grass").wrappedValue == "on" }, set: { binding("grass").wrappedValue = $0 ? "on" : "" }))
        }
    }
}

@MainActor
struct MetricSection: View {
    @EnvironmentObject var store: NativeStore
    var calculation: Calculation
    private let preferred = ["ground_roll_ft", "total_clear_50ft_ft", "total_to_clear_50ft_ft", "Percent BHP", "KTAS", "GPH", "time_to_climb_min", "fuel_used_gal_climb_only", "fuel_used_gal_with_start_taxi_takeoff", "distance_to_climb_nm"]
    private var keys: [String] {
        let numeric = calculation.result.object.keys.filter { calculation.result[$0].double != nil }
        return preferred.filter(numeric.contains) + numeric.filter { !preferred.contains($0) }.sorted()
    }
    var body: some View {
        Section(store.label("Result", "结果")) {
            ForEach(keys, id: \.self) { key in
                LabeledContent {
                    Text(n(calculation.result[key].double!) + " " + unitFor(key)).monospacedDigit()
                        .foregroundStyle(.primary).fixedSize(horizontal: true, vertical: false)
                } label: {
                    Text(fieldName(key, chinese: store.chinese)).fixedSize(horizontal: false, vertical: true)
                }
                .accessibilityElement(children: .combine).accessibilityIdentifier("metric-" + key)
            }
        }
    }
}

struct StepsSection: View {
    var steps: [MathStep]
    var body: some View {
        Section("Calculation steps / 计算步骤") {
            ForEach(steps) { step in
                VStack(alignment: .leading, spacing: 10) {
                    Text(step.title).font(.headline)
                    if let grid = step.grid { InterpolationGrid(grid: grid) }
                    if let url = URL(string: step.formula), url.scheme == "https" { Link("POH source", destination: url) }
                    else { Text(step.formula).font(.subheadline).foregroundStyle(.secondary) }
                    Text(step.value).font(.system(.body, design: .monospaced)).textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
                }.padding(.vertical, 6).accessibilityElement(children: .contain)
            }
        }
    }
}

struct InterpolationGrid: View {
    var grid: MathGrid
    var body: some View {
        Grid(horizontalSpacing: 12, verticalSpacing: 10) {
            GridRow { Text(grid.axis).foregroundStyle(.secondary); Text(n(grid.lowY)); Text(n(grid.highY)) }
            Divider().gridCellColumns(3)
            GridRow { Text(n(grid.lowX) + " ft").foregroundStyle(.secondary); Text(n(grid.q11)); Text(n(grid.q12)) }
            GridRow { Text(n(grid.highX) + " ft").foregroundStyle(.secondary); Text(n(grid.q21)); Text(n(grid.q22)) }
        }.font(.subheadline).monospacedDigit().frame(maxWidth: .infinity)
    }
}
