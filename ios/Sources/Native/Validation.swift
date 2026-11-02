import Foundation

enum NativeValidation {
    static let phases = ["takeoff", "landing", "cruise", "climb"]
    static let columns: [String: [String]] = [
        "takeoff": ["weight_lb", "pa_ft", "oat_c", "ground_ft", "total_ft", "lift_off_kias", "at_50ft_kias"],
        "landing": ["weight_lb", "pa_ft", "oat_c", "ground_ft", "total_ft", "at_50ft_kias"],
        "cruise": ["pa_ft", "isa_offset_c", "rpm", "percent_bhp", "ktas", "gph"],
        "climb": ["pa_ft", "std_temp_c", "climb_speed_kias", "rate_fpm", "time_from_sl_min", "fuel_from_sl_gal", "distance_from_sl_nm"]]
    static let climbRules = ["warm_temp_pct", "warm_temp_step_c", "start_taxi_takeoff_fuel_gal"]
    static func defaultClimb(model: String) -> J {
        .object(["mode": .string(model == "c172n" ? "builtin" : "none"), "source": .string(""), "conditions": .string(""), "rows": .array([])])
    }
    static let rules = ["headwind_pct", "headwind_step_kt", "headwind_max_kt", "tailwind_pct", "tailwind_step_kt", "tailwind_max_kt", "grass_pct"]
    static let wbFields = ["empty_weight_lb", "empty_moment_lb_in", "fuel_density_lb_gal", "fuel_arm_in", "max_ramp_lb", "max_takeoff_lb", "max_landing_lb", "usable_fuel_gal", "baggage_total_lb"]

    static func number(_ value: J, _ label: String, optional: Bool = false) throws -> Double? {
        if value == .null || value == .string("") {
            if optional { return nil }
            throw CalculationError("\(label): a number is required.")
        }
        guard let number = value.double, number.isFinite else { throw CalculationError("\(label): enter a finite number.") }
        return number
    }
    static func required(_ value: J, _ label: String) throws -> Double { try number(value, label)! }

    static func dataset(_ raw: J, phase: String, model: String) throws -> (J, [String]) {
        var parsed = raw
        var issues: [String] = []
        let mode = parsed["mode"].text
        guard ["none", "builtin", "manual", "c172m1974"].contains(mode) else { throw CalculationError("Invalid performance mode.") }
        for key in ["source", "conditions"] {
            if parsed[key] != .null { guard case .string = parsed[key] else { throw CalculationError("Invalid POH text: " + key) } }
            guard parsed[key].text.count <= 2000 else { throw CalculationError("POH text is too long.") }
            parsed[key] = .string(parsed[key].text.trimmingCharacters(in: .whitespacesAndNewlines))
        }
        for key in rules + climbRules + ["reference_weight_lb"] {
            let value = try number(parsed[key], key, optional: true)
            if let value {
                guard value >= 0, !(key.hasSuffix("_pct") && value > 100), !(key == "reference_weight_lb" && value == 0) else { throw CalculationError("Invalid correction / reference weight: " + key) }
                parsed[key] = .number(value)
            } else { parsed[key] = .null }
        }
        if parsed["grass_mode"] == .null { parsed["grass_mode"] = .string("none") }
        guard ["none", "ground_add", "both_percent"].contains(parsed["grass_mode"].text) else { throw CalculationError("Invalid grass correction mode.") }
        if parsed["rows"] != .null { guard case .array = parsed["rows"] else { throw CalculationError("POH rows must be an array") } }
        let rows = parsed["rows"].array
        guard rows.count <= 3000 else { throw CalculationError("At most 3000 POH rows are allowed.") }
        var normalized: [J] = [], seen = Set<[Double]>()
        for (index, row) in rows.enumerated() {
            var values: [String: J] = [:], incomplete = false
            for key in columns[phase] ?? [] {
                let value = try number(row[key], "Row \(index + 1) \(key)", optional: true)
                if let value {
                    let signed = ["pa_ft", "oat_c", "isa_offset_c", "std_temp_c"].contains(key)
                    let cumulative = key.hasSuffix("_from_sl_min") || key.hasSuffix("_from_sl_gal") || key.hasSuffix("_from_sl_nm")
                    if (!signed && !cumulative && value <= 0) || (cumulative && value < 0) { throw CalculationError("Invalid POH row value: " + key) }
                    values[key] = .number(value)
                } else { incomplete = true; values[key] = .null }
            }
            let result = J.object(values)
            normalized.append(result)
            if incomplete { issues.append("Row \(index + 1): fill every cell"); continue }
            if phase == "cruise" {
                guard result["percent_bhp"].double! <= 100 else { throw CalculationError("Power exceeds 100% BHP.") }
            } else if phase != "climb" {
                guard result["total_ft"].double! >= result["ground_ft"].double! else { throw CalculationError("50 ft distance cannot be below ground roll.") }
            }
            let keys = phase == "climb" ? ["pa_ft"] : phase == "cruise" ? ["pa_ft", "isa_offset_c", "rpm"] : ["weight_lb", "pa_ft", "oat_c"]
            guard seen.insert(keys.map { result[$0].double! }).inserted else { throw CalculationError("Duplicate POH table coordinates.") }
        }
        parsed["rows"] = .array(normalized)
        if mode == "none" { return (parsed, ["No performance table selected"] ) }
        if mode == "builtin" { return (parsed, model == "c172n" ? [] : ["Built-in data is C172N only"]) }
        if mode == "c172m1974" { return (parsed, model == "c172m" && phase != "climb" ? [] : ["No 1974 reference table for this model / phase"]) }
        for key in ["source", "conditions"] where parsed[key].text.isEmpty { issues.append("POH \(key) is required") }
        if rows.isEmpty { issues.append("Enter at least one complete POH row") }
        if phase == "climb" {
            for key in ["warm_temp_pct", "start_taxi_takeoff_fuel_gal"] where parsed[key] == .null { issues.append(key + ": required (enter 0 when the POH specifies none)") }
            if (parsed["warm_temp_pct"].double ?? 0) > 0 && (parsed["warm_temp_step_c"].double ?? 0) <= 0 { issues.append("A positive temperature step is required for a nonzero correction") }
            if normalized.count < 2 { issues.append("Climb requires at least two complete altitude rows") }
            if !normalized.contains(where: { $0.object.values.contains(.null) }) {
                let ordered = normalized.sorted { $0["pa_ft"].double! < $1["pa_ft"].double! }
                for (first, last) in zip(ordered, ordered.dropFirst()) {
                    for key in ["time_from_sl_min", "fuel_from_sl_gal", "distance_from_sl_nm"] where last[key].double! < first[key].double! { issues.append("Cumulative climb values cannot decrease: " + key) }
                }
                parsed["rows"] = .array(ordered)
            }
        } else if phase == "cruise" {
            if parsed["reference_weight_lb"] == .null { issues.append("Reference weight is required") }
        } else {
            for kind in ["headwind", "tailwind"] {
                let values = ["_pct", "_step_kt", "_max_kt"].map { parsed[kind + $0].double }
                if values.contains(where: { $0 != nil }) && (values[0] == nil || (values[1] ?? 0) <= 0 || (values[2] != nil && values[2]! <= 0)) { issues.append("\(kind): enter percentage and a positive knot step / maximum") }
            }
            if parsed["grass_mode"].text != "none" && parsed["grass_pct"] == .null { issues.append("Grass percentage is required") }
            if !normalized.contains(where: { $0.object.values.contains(.null) }) {
                for weight in Set(normalized.compactMap { $0["weight_lb"].double }) {
                    let group = normalized.filter { $0["weight_lb"].double == weight }
                    if group.count != Set(group.compactMap { $0["pa_ft"].double }).count * Set(group.compactMap { $0["oat_c"].double }).count { issues.append("\(n(weight)) lb: incomplete PA/OAT grid") }
                }
            }
        }
        return (parsed, issues)
    }

    static func profile(_ raw: J, catalogue: J) throws -> (J, [String]) {
        guard let model = catalogue.array.first(where: { $0["id"].text == raw["model_id"].text }) else { throw CalculationError("Choose an aircraft model.") }
        var result = model["template"], issues: [String] = []
        for key in ["id", "name", "registration", "serial_number", "wb_reference", "wb_date", "notes"] {
            if raw[key] != .null { guard case .string = raw[key] else { throw CalculationError("Invalid aircraft text: " + key) } }
            guard raw[key].text.count <= 2000 else { throw CalculationError("Aircraft text is too long: " + key) }
            result[key] = .string(raw[key].text.trimmingCharacters(in: .whitespacesAndNewlines))
        }
        guard !result["name"].text.isEmpty else { throw CalculationError("Aircraft name is required.") }
        if let year = try number(raw["year"], "Year", optional: true) {
            guard year.rounded() == year, (1900...2100).contains(year) else { throw CalculationError("Enter a four-digit aircraft year.") }
            result["year"] = .number(year)
            if let first = model["years"][0].double, let last = model["years"][1].double, !(first...last).contains(year) { issues.append("Model year mismatch: confirm serial number and model") }
        } else { result["year"] = .null }
        if result["registration"].text.isEmpty { issues.append("Registration is required") }
        if result["wb_reference"].text.isEmpty { issues.append("Aircraft W&B document / POH reference is required") }
        guard raw["wb"] != .null else { throw CalculationError("Aircraft W&B configuration is required.") }
        var wb = result["wb"]
        for key in wbFields {
            if let value = try number(raw["wb"][key], key, optional: true) {
                if ["empty_weight_lb", "fuel_density_lb_gal", "max_ramp_lb", "max_takeoff_lb", "max_landing_lb"].contains(key), value <= 0 { throw CalculationError(key + " must be positive") }
                if ["usable_fuel_gal", "baggage_total_lb"].contains(key), value < 0 { throw CalculationError(key + " cannot be negative") }
                wb[key] = .number(value)
            } else { wb[key] = .null; issues.append(key + ": required") }
        }
        if let ramp = wb["max_ramp_lb"].double, let takeoff = wb["max_takeoff_lb"].double, ramp < takeoff { throw CalculationError("Maximum ramp weight cannot be below takeoff weight.") }
        guard raw["wb"]["stations"].array.count == 6 else { throw CalculationError("Six loading stations are required.") }
        var stations: [J] = []
        for (index, template) in wb["stations"].array.enumerated() {
            let supplied = raw["wb"]["stations"][index]
            guard supplied["key"] == template["key"], case .bool = supplied["enabled"] else { throw CalculationError("Invalid loading stations / order.") }
            var station = template
            station["enabled"] = supplied["enabled"]
            for key in ["arm_in", "max_weight_lb"] {
                if let value = try number(supplied[key], station["label"].text + " " + key, optional: true) {
                    if key == "max_weight_lb", value < 0 { throw CalculationError("Station limit cannot be negative") }
                    station[key] = .number(value)
                } else { station[key] = .null; if key == "arm_in" && station["enabled"].flag { issues.append(station["label"].text + " arm: required") } }
            }
            stations.append(station)
        }
        wb["stations"] = .array(stations)
        if raw["wb"]["cg_limits"] != .null { guard case .array = raw["wb"]["cg_limits"] else { throw CalculationError("CG envelope must be an array") } }
        guard raw["wb"]["cg_limits"].array.count <= 30 else { throw CalculationError("At most 30 CG envelope rows are allowed") }
        var limits: [J] = []
        for row in raw["wb"]["cg_limits"].array {
            let weight = try number(row["weight_lb"], "CG weight", optional: true)
            let forward = try number(row["forward_in"], "CG forward", optional: true)
            let aft = try number(row["aft_in"], "CG aft", optional: true)
            if let weight, let forward, let aft {
                guard weight >= 0, forward < aft else { throw CalculationError("Invalid CG envelope bounds") }
                if let previous = limits.last?["weight_lb"].double, previous >= weight { throw CalculationError("CG envelope weights must increase") }
                limits.append(.numbers(["weight_lb": weight, "forward_in": forward, "aft_in": aft]))
            } else { issues.append("Complete every CG envelope row") }
        }
        if limits.count < 2 { issues.append("CG envelope requires at least two complete rows") }
        for key in ["max_takeoff_lb", "max_landing_lb"] {
            if let limit = wb[key].double, let top = limits.last?["weight_lb"].double, top < limit { issues.append("CG envelope must cover " + key) }
        }
        wb["cg_limits"] = .array(limits); result["wb"] = wb
        for phase in phases {
            let fallback = phase == "climb" ? defaultClimb(model: result["model_id"].text) : result["performance"][phase]
            let supplied = raw["performance"][phase] == .null ? fallback : raw["performance"][phase]
            let (table, _) = try dataset(supplied, phase: phase, model: result["model_id"].text)
            result["performance"][phase] = table
            if table["mode"].text == "c172m1974", result["year"].double != 1974 { issues.append("Model year mismatch: 1974 reference requires year 1974") }
        }
        return (result, issues)
    }
}
