import Foundation

extension NativeEngine {
    static func cgLimits(_ points: [J], weight: Double) -> (Double, Double) {
        if weight <= points[0]["weight_lb"].double! { return (points[0]["forward_in"].double!, points[0]["aft_in"].double!) }
        for index in 1..<points.count where weight <= points[index]["weight_lb"].double! {
            let low = points[index - 1], high = points[index]
            return (mix(weight, low["weight_lb"].double!, high["weight_lb"].double!, low["forward_in"].double!, high["forward_in"].double!),
                    mix(weight, low["weight_lb"].double!, high["weight_lb"].double!, low["aft_in"].double!, high["aft_in"].double!))
        }
        return (points.last!["forward_in"].double!, points.last!["aft_in"].double!)
    }

    func weightBalance(_ form: J, profile supplied: J?) throws -> Calculation {
        var profile = supplied ?? data["profiles"][0]
        if supplied == nil {
            profile["name"] = .string("C172N Demo")
            profile["registration"] = .string("DEMO")
            let empty = try Self.num(form, "empty_weight_lbs", default: 1541)
            profile["wb"]["empty_weight_lb"] = .number(empty)
            profile["wb"]["empty_moment_lb_in"] = .number(empty * (try Self.num(form, "empty_arm_in", default: 38.2)))
        }
        let (normalized, issues) = try NativeValidation.profile(profile, catalogue: data["catalogue"])
        guard issues.isEmpty else { throw CalculationError("Complete aircraft profile: " + issues.joined(separator: "; ")) }
        profile = normalized
        let wb = profile["wb"], points = wb["cg_limits"].array
        let loadKeys = wb["stations"].array.map { $0["key"].text } + ["fuel_gal", "taxi_fuel_gal", "trip_fuel_gal"]
        var loads: [String: Double] = [:]
        for key in loadKeys {
            let value = try Self.num(form, key)
            guard value >= 0 else { throw CalculationError(key + ": enter a nonnegative load.") }
            loads[key] = value
        }
        guard loads["taxi_fuel_gal"]! + loads["trip_fuel_gal"]! <= loads["fuel_gal"]! + 1e-9 else { throw CalculationError("Taxi plus trip fuel cannot exceed fuel on board.") }
        var rows: [J] = [], phases: [J] = [], explanations: [J] = [], steps: [MathStep] = [], loadingErrors: [String] = []
        var weight = wb["empty_weight_lb"].double!, moment = wb["empty_moment_lb_in"].double!
        func load(_ name: String, arm: Double, amount: Double, exactMoment: Double? = nil, kind: String = "load") {
            let m = exactMoment ?? arm * amount
            rows.append(.object(["item": .string(name), "arm": .number(arm), "weight": .number(amount), "moment": .number(m), "cg": .null, "kind": .string(kind)]))
            if exactMoment != nil {
                steps.append(MathStep(title: "Empty aircraft record", formula: "Use the recorded empty moment; empty CG = moment ÷ weight", value: "Moment: \(n(m)) lb-in\nCG: \(n(m)) ÷ \(n(amount)) = \(n(arm)) in"))
            } else {
                steps.append(MathStep(title: "Moment — " + name, formula: "Moment = weight × arm", value: "\(n(amount)) × \(n(arm)) = \(n(m)) lb-in"))
            }
        }
        load("Empty Aircraft", arm: moment / weight, amount: weight, exactMoment: moment)
        for station in wb["stations"].array {
            let amount = loads[station["key"].text]!
            if !station["enabled"].flag {
                guard amount == 0 else { throw CalculationError(station["label"].text + " is not enabled for this aircraft.") }
                continue
            }
            if let maximum = station["max_weight_lb"].double, amount > maximum { loadingErrors.append(station["label"].text + " OVER LIMIT") }
            let arm = station["arm_in"].double!
            load(station["label"].text, arm: arm, amount: amount)
            weight += amount; moment += amount * arm
        }
        if loads["baggage1_weight_lbs"]! + loads["baggage2_weight_lbs"]! > wb["baggage_total_lb"].double! { loadingErrors.append("COMBINED BAGGAGE OVER LIMIT") }
        if loads["fuel_gal"]! > wb["usable_fuel_gal"].double! { loadingErrors.append("FUEL EXCEEDS USABLE CAPACITY") }
        func phase(_ name: String, maximum: Double?, previous: (Double, Double)? = nil, delta: (Double, Double) = (0, 0)) throws {
            guard weight > 0 else { throw CalculationError("Phase weight must be positive.") }
            let cg = moment / weight, (forward, aft) = Self.cgLimits(points, weight: weight)
            rows.append(.object(["item": .string(name == "ZFW" ? "Zero Fuel" : name), "arm": .null, "weight": .number(weight), "moment": .number(moment), "cg": .number(cg), "kind": .string("total")]))
            var errors = loadingErrors
            if let maximum, weight > maximum { errors.append("OVER MAX " + name.uppercased() + " WEIGHT") }
            if weight < points[0]["weight_lb"].double! { errors.append("BELOW CG ENVELOPE WEIGHT RANGE") }
            if name != "Ramp", weight > points.last!["weight_lb"].double! { errors.append("ABOVE CG ENVELOPE WEIGHT RANGE") }
            if cg < forward { errors.append("CG FORWARD OF LIMIT") }
            if cg > aft { errors.append("CG AFT OF LIMIT") }
            let message = errors.isEmpty ? (name == "ZFW" ? "CG within limits; no separate ZFW weight limit configured" : "Within configured limits") : errors.joined(separator: "; ")
            phases.append(.object(["phase": .string(name), "weight": .number(weight), "max_weight": maximum.map(J.number) ?? .null,
                                   "cg": .number(cg), "forward_limit": .number(forward), "aft_limit": .number(aft), "limit": .string("\(n(forward)) - \(n(aft))"),
                                   "status": .string(errors.isEmpty ? "OK" : "FAIL"), "message": .string(message)]))
            var lines: [String]
            if let previous {
                lines = ["Weight: \(n(previous.0)) + (\(n(delta.0))) = \(n(weight)) lb", "Moment: \(n(previous.1)) + (\(n(delta.1))) = \(n(moment)) lb-in"]
            } else {
                let loading = rows.filter { $0["kind"].text == "load" }
                lines = ["Weight: " + loading.map { n($0["weight"].double!) }.joined(separator: " + ") + " = \(n(weight)) lb",
                         "Moment: " + loading.map { n($0["moment"].double!) }.joined(separator: " + ") + " = \(n(moment)) lb-in"]
            }
            lines.append("CG: \(n(moment)) ÷ \(n(weight)) = \(n(cg)) in")
            explanations.append(.object(["title": .string(name), "lines": .array(lines.map(J.string))]))
            steps.append(MathStep(title: name, formula: "CG = total moment ÷ total weight", value: lines.joined(separator: "\n")))
        }
        try phase("ZFW", maximum: nil)
        for (name, key, sign, maximumKey) in [("Ramp", "fuel_gal", 1.0, "max_ramp_lb"), ("Takeoff", "taxi_fuel_gal", -1.0, "max_takeoff_lb"), ("Landing", "trip_fuel_gal", -1.0, "max_landing_lb")] {
            let fuel = loads[key]! * wb["fuel_density_lb_gal"].double!, arm = wb["fuel_arm_in"].double!
            steps.append(MathStep(title: key + " conversion", formula: "US gal × lb/US gal = fuel weight", value: "\(n(loads[key]!)) × \(n(wb["fuel_density_lb_gal"].double!)) = \(n(fuel)) lb"))
            let previous = (weight, moment), delta = (sign * fuel, sign * fuel * arm)
            load(name == "Ramp" ? "Fuel" : name == "Takeoff" ? "Taxi Fuel" : "Trip Fuel", arm: arm, amount: delta.0, kind: sign > 0 ? "load" : "burn")
            weight += delta.0; moment += delta.1
            try phase(name, maximum: wb[maximumKey].double, previous: previous, delta: delta)
        }
        let floor = max(points[0]["weight_lb"].double!, min(phases.compactMap { $0["weight"].double }.min()! * 0.85, points.last!["weight_lb"].double! * 0.8))
        let (forward, aft) = Self.cgLimits(points, weight: floor)
        var envelope = [J.numbers(["cg": forward, "weight": floor])]
        envelope += points.filter { $0["weight_lb"].double! > floor }.map { .numbers(["cg": $0["forward_in"].double!, "weight": $0["weight_lb"].double!]) }
        envelope += points.reversed().filter { $0["weight_lb"].double! > floor }.map { .numbers(["cg": $0["aft_in"].double!, "weight": $0["weight_lb"].double!]) }
        envelope.append(.numbers(["cg": aft, "weight": floor]))
        let summary = J.numbers(["zero_fuel_cg_in": phases[0]["cg"].double!, "ramp_cg_in": phases[1]["cg"].double!, "takeoff_cg_in": phases[2]["cg"].double!,
                                 "landing_cg_in": phases[3]["cg"].double!, "takeoff_weight_lbs": phases[2]["weight"].double!, "landing_weight_lbs": phases[3]["weight"].double!])
        let plotPoints = phases.map { J.object(["label": $0["phase"], "cg": $0["cg"], "weight": $0["weight"], "status": $0["status"]]) }
        let result = J.object(["kind": .string("weight_balance"), "aircraft_name": profile["name"], "registration": profile["registration"], "summary": summary,
                               "rows": .array(rows), "envelope": .array(phases), "explanations": .array(explanations), "plot": .object(["envelope": .array(envelope), "points": .array(plotPoints)])])
        return Calculation(result: result, steps: steps)
    }
}
