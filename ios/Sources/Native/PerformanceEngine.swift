import Foundation

struct NativeEngine {
    let data: J
    init(data: J) { self.data = data }
    init(bundle: Bundle = .main) throws {
        guard let url = bundle.url(forResource: "NativeData", withExtension: "json") else { throw CalculationError("Native POH data is missing.") }
        data = try J.decode(Data(contentsOf: url))
    }
    static func bracket(_ values: [Double], _ x: Double, _ label: String) throws -> (Double, Double) {
        let sorted = Array(Set(values)).sorted()
        guard x.isFinite, let first = sorted.first, let last = sorted.last, x >= first, x <= last else { throw CalculationError("\(label) is outside the recorded POH range.") }
        if sorted.contains(x) { return (x, x) }
        return (sorted.last(where: { $0 < x })!, sorted.first(where: { $0 > x })!)
    }
    static func mix(_ x: Double, _ low: Double, _ high: Double, _ first: Double, _ last: Double) -> Double {
        low == high ? first : first + (x - low) / (high - low) * (last - first)
    }
    static func math(_ x: Double, _ low: Double, _ high: Double, _ first: Double, _ last: Double) -> String {
        if low == high { return "Exact \(n(x)): \(n(first))" }
        return "\(n(first)) + (\(n(x)) - \(n(low))) / (\(n(high)) - \(n(low))) × (\(n(last)) - \(n(first))) = \(n(mix(x, low, high, first, last)))"
    }
    static func isa(_ altitude: Double) -> Double { 15 - 2 * altitude / 1000 }
    static func num(_ form: J, _ key: String, default value: Double = 0) throws -> Double {
        try NativeValidation.number(form[key], key, optional: true) ?? value
    }

    struct Wind {
        var head = 0.0, tail = 0.0
        var cross: Double? = nil
        var steps: [MathStep] = []
    }
    static func wind(_ form: J) throws -> Wind {
        guard let runway = try NativeValidation.number(form["runway_heading_deg"], "Runway", optional: true),
              var direction = try NativeValidation.number(form["wind_direction_deg"], "Wind direction", optional: true),
              let speed = try NativeValidation.number(form["wind_speed_kt"], "Wind speed", optional: true) else { return Wind() }
        guard (0...360).contains(runway), (0...360).contains(direction), speed >= 0 else { throw CalculationError("Invalid runway / wind direction / wind speed.") }
        let heading = (1...36).contains(runway) ? runway * 10 : runway
        var steps = [MathStep(title: "Runway heading", formula: "Runway number × 10 = magnetic heading", value: "\(n(runway)) → \(n(heading))° M")]
        let reference = form["wind_reference"].text.isEmpty ? "magnetic" : form["wind_reference"].text
        if reference == "true" {
            let variation = try NativeValidation.required(form["magnetic_variation_deg"], "Airport magnetic variation")
            let side = form["variation_direction"].text.isEmpty ? "east" : form["variation_direction"].text
            guard (0...180).contains(variation), ["east", "west"].contains(side) else { throw CalculationError("Enter variation 0–180°, east or west.") }
            let magnetic = ((direction - (side == "east" ? variation : -variation)).truncatingRemainder(dividingBy: 360) + 360).truncatingRemainder(dividingBy: 360)
            steps.append(MathStep(title: "True → magnetic", formula: "Magnetic = True − East, or True + West (mod 360)", value: "\(n(direction))° T \(side == "east" ? "−" : "+") \(n(variation))° = \(n(magnetic))° M"))
            direction = magnetic
        } else if reference != "magnetic" { throw CalculationError("Wind reference must be True or Magnetic.") }
        let angle = abs(((direction - heading + 540).truncatingRemainder(dividingBy: 360)) - 180)
        let signed = speed * cos(angle * .pi / 180)
        let cross = abs(speed * sin(angle * .pi / 180))
        steps += [MathStep(title: "Wind angle", formula: "Smallest difference between magnetic wind and runway", value: "Wind \(n(direction))° M; runway \(n(heading))° M; angle \(n(angle))°"),
                  MathStep(title: "Headwind", formula: "Wind speed × cos(angle)", value: "\(n(speed)) × cos(\(n(angle))°) = \(n(signed)) kt"),
                  MathStep(title: "Crosswind", formula: "|Wind speed × sin(angle)|", value: "|\(n(speed)) × sin(\(n(angle))°)| = \(n(cross)) kt")]
        return Wind(head: max(signed, 0), tail: max(-signed, 0), cross: cross, steps: steps)
    }

    static func grid(_ rows: [J], field: String, x: Double, y: Double, second: String = "oat_c", label: String) throws -> (Double, MathStep) {
        let (a, b) = try bracket(rows.compactMap { $0["pa_ft"].double }, x, "Pressure altitude")
        let (c, d) = try bracket(rows.compactMap { $0[second].double }, y, second)
        func cell(_ pa: Double, _ temp: Double) throws -> Double {
            guard let value = rows.first(where: { $0["pa_ft"].double == pa && $0[second].double == temp })?[field].double else { throw CalculationError("Missing POH cell: \(n(pa)), \(n(temp)), \(field)") }
            return value
        }
        let q11 = try cell(a, c), q12 = try cell(a, d), q21 = try cell(b, c), q22 = try cell(b, d)
        let low = mix(x, a, b, q11, q21), high = mix(x, a, b, q12, q22)
        let result = mix(y, c, d, low, high)
        let step = MathStep(title: label + " POH interpolation", formula: "Altitude interpolation, then \(second == "oat_c" ? "OAT" : "headwind") interpolation",
                            value: "1. At \(n(c)): \(math(x, a, b, q11, q21))\n2. At \(n(d)): \(math(x, a, b, q12, q22))\n3. \(math(y, c, d, low, high))",
                            grid: MathGrid(axis: second == "oat_c" ? "PA / OAT" : "PA / Headwind", lowX: a, highX: b, lowY: c, highY: d, q11: q11, q12: q12, q21: q21, q22: q22))
        return (result, step)
    }

    func calculate(_ phase: String, form: J, profile supplied: J? = nil) throws -> Calculation {
        var profile = supplied
        if supplied == nil, !form["aircraft_profile"].text.isEmpty {
            profile = try J.decode(Data(form["aircraft_profile"].text.utf8))
        }
        var model = "c172n", table = J.null, mode = "builtin"
        if let raw = profile {
            let (parsed, issues) = try NativeValidation.profile(raw, catalogue: data["catalogue"])
            profile = parsed; model = parsed["model_id"].text
            if issues.contains(where: { $0.hasPrefix("Model year mismatch") }) { throw CalculationError("Confirm aircraft model and year before using POH tables.") }
            if phase == "climb", model != "c172n" { throw CalculationError("Climb tables are currently C172N only.") }
            if NativeValidation.phases.contains(phase) {
                let (validated, problems) = try NativeValidation.dataset(parsed["performance"][phase], phase: phase, model: model)
                guard problems.isEmpty else { throw CalculationError(problems.joined(separator: "; ")) }
                table = validated; mode = table["mode"].text
            }
        }
        if phase == "weight-balance" { return try weightBalance(form, profile: profile) }
        if phase == "climb" { return try climb(form) }
        if mode == "builtin" { table = data["builtin"][phase] }
        if phase == "cruise" { return try cruise(form, table: table, mode: mode) }
        guard ["takeoff", "landing"].contains(phase) else { throw CalculationError("Unknown calculation.") }
        let wind = try Self.wind(form)
        if mode == "c172m1974" { return try referenceDistance(phase, form: form, wind: wind) }
        return try distance(phase, form: form, wind: wind, table: table, builtin: mode == "builtin")
    }

    func distance(_ phase: String, form: J, wind: Wind, table: J, builtin: Bool) throws -> Calculation {
        let weight = try Self.num(form, "weight_lbs", default: 2300)
        let pa = try Self.num(form, "pressure_altitude_ft"), oat = try Self.num(form, "oat_c")
        let weights = Array(Set(table["rows"].array.compactMap { $0["weight_lb"].double })).sorted()
        guard weight > 0, let selected = weights.first(where: { $0 >= (builtin && phase == "landing" ? 2300 : weight) }) else { throw CalculationError("Weight exceeds the POH table maximum or is not positive.") }
        let rows = table["rows"].array.filter { $0["weight_lb"].double == selected }
        let (ground, groundStep) = try Self.grid(rows, field: "ground_ft", x: pa, y: oat, label: "Ground")
        let (total, totalStep) = try Self.grid(rows, field: "total_ft", x: pa, y: oat, label: "50 ft")
        var steps = [MathStep(title: "POH source", formula: table["source"].text, value: table["conditions"].text),
                     MathStep(title: "Weight table", formula: "Next table not below actual weight", value: "\(n(weight)) → \(n(selected)) lb" )] + wind.steps + [groundStep, totalStep]
        var factor = 1.0
        for (kind, speed, sign) in [("headwind", wind.head, -1.0), ("tailwind", wind.tail, 1.0)] where speed > 1e-9 {
            let maximum = builtin && phase == "takeoff" && kind == "tailwind" ? nil : table[kind + "_max_kt"].double
            guard let percent = table[kind + "_pct"].double, let step = table[kind + "_step_kt"].double, step > 0 else { throw CalculationError("No \(kind) correction is recorded.") }
            if let maximum, speed > maximum { throw CalculationError("\(kind.capitalized) exceeds the recorded POH limit.") }
            factor = 1 + sign * percent / 100 * speed / step
            steps.append(MathStep(title: "Wind factor", formula: "1 \(sign < 0 ? "−" : "+") (percentage / 100) × (wind / knot step)", value: "1 \(sign < 0 ? "−" : "+") (\(n(percent)) / 100.0) × (\(n(speed)) / \(n(step))) = \(n(factor * 100))%"))
        }
        guard factor > 0 else { throw CalculationError("Wind correction would produce a nonpositive distance.") }
        var correctedGround = ground * factor, correctedTotal = total * factor
        steps.append(MathStep(title: "After wind", formula: "POH distance × wind factor", value: "Ground: \(n(ground)) × \(n(factor * 100))% = \(n(correctedGround)) ft\n50 ft: \(n(total)) × \(n(factor * 100))% = \(n(correctedTotal)) ft"))
        if form["grass"].text == "on" || form["grass"].flag {
            guard table["grass_mode"].text != "none", let percentage = table["grass_pct"].double else { throw CalculationError("No grass correction is recorded.") }
            let groundAdd = correctedGround * percentage / 100
            let totalAdd = (table["grass_mode"].text == "ground_add" ? correctedGround : correctedTotal) * percentage / 100
            steps.append(MathStep(title: "Grass add", formula: table["grass_mode"].text == "ground_add" ? "Percentage of corrected ground roll added to both distances" : "Each corrected distance × grass percentage", value: "Ground: \(n(correctedGround)) + \(n(groundAdd)) = \(n(correctedGround + groundAdd)) ft\n50 ft: \(n(correctedTotal)) + \(n(totalAdd)) = \(n(correctedTotal + totalAdd)) ft\nPercentage: \(n(percentage))%"))
            correctedGround += groundAdd; correctedTotal += totalAdd
        }
        var values = ["input_weight_lbs": weight, "selected_table_lbs": selected, "ground_roll_ft": correctedGround,
                      phase == "takeoff" ? "total_clear_50ft_ft" : "total_to_clear_50ft_ft": correctedTotal,
                      "headwind_component_kt": wind.head, "tailwind_component_kt": wind.tail]
        for field in phase == "takeoff" ? ["lift_off_kias", "at_50ft_kias"] : ["at_50ft_kias"] {
            let (speed, step) = try Self.grid(rows, field: field, x: pa, y: oat, label: field)
            values[field] = speed
            if !builtin { steps.append(step) }
        }
        if let cross = wind.cross { values["crosswind_component_kt"] = cross }
        if builtin {
            for key in Array(values.keys) where key != "input_weight_lbs" { values[key] = rounded1(values[key]!) }
        }
        return Calculation(result: .numbers(values), steps: steps)
    }

    func cruise(_ form: J, table: J, mode: String) throws -> Calculation {
        let altitude = try Self.num(form, "pressure_altitude_ft"), rpm = try Self.num(form, "rpm")
        var lowAlt = try Self.num(form, "lower_oat_altitude_ft"), highAlt = try Self.num(form, "upper_oat_altitude_ft")
        var lowOAT = try Self.num(form, "lower_oat_c"), highOAT = try Self.num(form, "upper_oat_c")
        if lowAlt > highAlt { swap(&lowAlt, &highAlt); swap(&lowOAT, &highOAT) }
        guard lowAlt < highAlt, altitude >= lowAlt, altitude <= highAlt else { throw CalculationError("Pressure altitude must lie between two different OAT altitude points.") }
        let oat = Self.mix(altitude, lowAlt, highAlt, lowOAT, highOAT), standard = Self.isa(altitude), offset = oat - standard
        var steps = [MathStep(title: "OAT interpolation", formula: "Lower OAT + altitude ratio × OAT difference", value: Self.math(altitude, lowAlt, highAlt, lowOAT, highOAT) + " °C"),
                     MathStep(title: "ISA offset", formula: "ISA = 15 − 2 × altitude / 1000; offset = OAT − ISA", value: "15.0 − 2.0 × \(n(altitude / 1000)) = \(n(standard)) °C\n\(n(oat)) − (\(n(standard))) = \(n(offset)) °C")]
        let reference = mode == "c172m1974"
        if !reference {
            var conditions = table["conditions"].text
            if let weight = table["reference_weight_lb"].double { conditions += "\nReference weight: \(n(weight)) lb" }
            steps.insert(MathStep(title: "POH source and conditions", formula: table["source"].text, value: conditions), at: 0)
        }
        var rows = table["rows"].array
        if reference {
            guard abs(offset) <= 0.050000001 else { throw CalculationError("1974 cruise reference is standard-day only: interpolated OAT must be \(n(standard)) °C.") }
            rows = data["reference"]["cruise"]["rows"].array.map { row in
                .numbers(["pa_ft": row[0].double!, "rpm": row[1].double!, "percent_bhp": row[2].double!, "ktas": row[3].double!, "gph": row[4].double!, "isa_offset_c": 0])
            }
        }
        let (a, b) = try Self.bracket(rows.compactMap { $0["pa_ft"].double }, altitude, "Pressure altitude")
        let fields = ["percent_bhp", "ktas", "gph"]
        func atAltitude(_ pa: Double) throws -> [Double] {
            let group = rows.filter { $0["pa_ft"].double == pa }
            let (c, d) = try Self.bracket(group.compactMap { $0["isa_offset_c"].double }, reference ? 0 : offset, "ISA offset")
            func atTemperature(_ temperature: Double) throws -> [Double] {
                let block = group.filter { $0["isa_offset_c"].double == temperature }
                let (r0, r1) = try Self.bracket(block.compactMap { $0["rpm"].double }, rpm, "RPM")
                let first = block.first { $0["rpm"].double == r0 }!, last = block.first { $0["rpm"].double == r1 }!
                let values = fields.map { Self.mix(rpm, r0, r1, first[$0].double!, last[$0].double!) }
                steps.append(MathStep(title: "RPM at \(n(pa)) ft / ISA \(n(temperature)) °C", formula: reference ? "Interpolate % BHP, TAS MPH and US gal/h" : "Interpolate % BHP, KTAS and US gal/h", value: fields.map { $0 + ": " + Self.math(rpm, r0, r1, first[$0].double!, last[$0].double!) }.joined(separator: "\n")))
                return values
            }
            let first = try atTemperature(c)
            let last = try (c == d ? first : atTemperature(d))
            let result = zip(first, last).map { Self.mix(reference ? 0 : offset, c, d, $0.0, $0.1) }
            if c != d { steps.append(MathStep(title: "Temperature at \(n(pa)) ft", formula: "Interpolate between ISA blocks", value: fields.indices.map { fields[$0] + ": " + Self.math(offset, c, d, first[$0], last[$0]) }.joined(separator: "\n"))) }
            return result
        }
        let first = try atAltitude(a)
        let last = try (a == b ? first : atAltitude(b))
        var result = zip(first, last).map { Self.mix(altitude, a, b, $0.0, $0.1) }
        steps.append(MathStep(title: "Altitude interpolation", formula: "Interpolate between PA tables", value: fields.indices.map { fields[$0] + ": " + Self.math(altitude, a, b, first[$0], last[$0]) }.joined(separator: "\n")))
        if reference {
            guard result[0] <= 75 + 1e-9 else { throw CalculationError("1974 normal cruise reference is limited to 75% BHP.") }
            steps.insert(MathStep(title: "1974 source and conditions", formula: data["reference"]["cruise"]["source_url"].text, value: data["reference"]["cruise"]["conditions"].text), at: 0)
            steps.append(MathStep(title: "TAS unit conversion", formula: "KTAS = MPH / (1852 / 1609.344)", value: "\(n(result[1])) MPH / 1.150779448 = \(n(result[1] / (1852 / 1609.344))) KTAS"))
            result[1] /= 1852 / 1609.344
        }
        var values = ["Pressure altitude ft": altitude, "OAT at altitude C": oat, "ISA temp at altitude C": standard,
                      "Temp offset from ISA C": offset, "Percent BHP": result[0], "KTAS": result[1], "GPH": result[2]]
        if mode == "builtin" { values = values.mapValues(rounded1) }
        return Calculation(result: .numbers(values), steps: steps)
    }

    func referenceDistance(_ phase: String, form: J, wind: Wind) throws -> Calculation {
        let weight = try Self.num(form, "weight_lbs", default: 2300), pa = try Self.num(form, "pressure_altitude_ft"), oat = try Self.num(form, "oat_c")
        guard weight > 0, weight <= 2300, (0...7500).contains(pa), wind.tail <= 1e-9 else { throw CalculationError("1974 reference requires weight ≤2300 lb, PA 0–7500 ft, and no tailwind.") }
        let source = data["reference"][phase]
        var steps = [MathStep(title: "1974 reference source", formula: source["source_url"].text, value: source["conditions"].text)] + wind.steps
        var ground: Double, total: Double, speed: Double, selected = 2300.0
        if phase == "takeoff" {
            guard wind.head <= 20 else { throw CalculationError("1974 takeoff headwind range is 0–20 kt.") }
            let sourceRows = source["rows"].array
            selected = Array(Set(sourceRows.compactMap { $0[0].double })).sorted().first { $0 >= weight }!
            let rows: [J] = sourceRows.filter { $0[0].double == selected }.map { row in .numbers(["pa_ft": row[1].double!, "headwind_kt": row[2].double!, "ground_ft": row[3].double!, "total_ft": row[4].double!]) }
            let g = try Self.grid(rows, field: "ground_ft", x: pa, y: wind.head, second: "headwind_kt", label: "Ground")
            let t = try Self.grid(rows, field: "total_ft", x: pa, y: wind.head, second: "headwind_kt", label: "50 ft")
            ground = g.0; total = t.0; steps += [MathStep(title: "Weight table", formula: "Next table not below actual weight", value: "\(n(weight)) → \(n(selected)) lb"), g.1, t.1]
            let delta = max(oat - Self.isa(pa), 0) * 1.8, factor = 1 + 0.1 * delta / 25
            steps.append(MathStep(title: "Warm-temperature correction", formula: "+10% per 25°F above ISA; no cold reduction", value: "ISA: \(n(Self.isa(pa))) °C\nmax(\(n(oat)) − \(n(Self.isa(pa))), 0.0) × 1.8 = \(n(delta)) °F\n1.0 + 0.1 × \(n(delta)) / 25.0 = \(n(factor * 100))%\nGround \(n(ground)) × \(n(factor * 100))% = \(n(ground * factor)) ft\n50 ft \(n(total)) × \(n(factor * 100))% = \(n(total * factor)) ft"))
            ground *= factor; total *= factor
            speed = sourceRows.first { $0[0].double == selected }![5].double!
        } else {
            guard abs(oat - Self.isa(pa)) <= 0.050000001 else { throw CalculationError("1974 landing is standard-day only: OAT must be \(n(Self.isa(pa))) °C.") }
            let rows = source["rows"].array
            let (a, b) = try Self.bracket(rows.compactMap { $0[1].double }, pa, "Pressure altitude")
            let first = rows.first { $0[1].double == a }!, last = rows.first { $0[1].double == b }!
            ground = Self.mix(pa, a, b, first[3].double!, last[3].double!)
            total = Self.mix(pa, a, b, first[4].double!, last[4].double!)
            steps.append(MathStep(title: "Landing altitude interpolation", formula: "2300 lb standard-day table", value: "Ground: " + Self.math(pa, a, b, first[3].double!, last[3].double!) + "\n50 ft: " + Self.math(pa, a, b, first[4].double!, last[4].double!)))
            let factor = 1 - 0.1 * wind.head / 5
            guard factor > 0 else { throw CalculationError("Wind correction would produce a nonpositive distance.") }
            steps.append(MathStep(title: "After headwind", formula: "−10% per 5 kt headwind", value: "1.0 − 0.1 × (\(n(wind.head)) / 5.0) = \(n(factor * 100))%\nGround: \(n(ground)) → \(n(ground * factor)) ft\n50 ft: \(n(total)) → \(n(total * factor)) ft"))
            ground *= factor; total *= factor; speed = 70
        }
        if form["grass"].text == "on" || form["grass"].flag {
            let fraction = phase == "takeoff" ? 0.07 : 0.20, addition = total * fraction
            steps.append(MathStep(title: "Dry-grass add", formula: "Percentage of total over-50-ft distance added to BOTH distances", value: "\(n(total)) × \(n(fraction * 100))% = \(n(addition)) ft\nGround: \(n(ground)) + \(n(addition)) = \(n(ground + addition)) ft\n50 ft: \(n(total)) + \(n(addition)) = \(n(total + addition)) ft"))
            ground += addition; total += addition
        }
        let kias = speed / (1852 / 1609.344)
        steps.append(MathStep(title: "IAS unit conversion", formula: "KIAS = MPH / 1.150779448", value: "\(n(speed)) / 1.150779448 = \(n(kias)) KIAS"))
        var values = ["input_weight_lbs": weight, "selected_table_lbs": selected, "ground_roll_ft": ground,
                      phase == "takeoff" ? "total_clear_50ft_ft" : "total_to_clear_50ft_ft": total,
                      phase == "takeoff" ? "at_50ft_kias" : "approach_kias": kias,
                      "headwind_component_kt": wind.head, "tailwind_component_kt": wind.tail]
        if let cross = wind.cross { values["crosswind_component_kt"] = cross }
        return Calculation(result: .numbers(values), steps: steps)
    }

    func climb(_ form: J) throws -> Calculation {
        let start = try Self.num(form, "pressure_altitude_ft"), target = try Self.num(form, "target_altitude_ft"), oat = try Self.num(form, "oat_c")
        guard target > start else { throw CalculationError("Target altitude must be above starting pressure altitude.") }
        let rows = data["climb"].array
        var steps: [MathStep] = []
        func at(_ altitude: Double, name: String) throws -> [String: Double] {
            let (a, b) = try Self.bracket(rows.compactMap { $0["pa_ft"].double }, altitude, "Climb pressure altitude")
            let first = rows.first { $0["pa_ft"].double == a }!, last = rows.first { $0["pa_ft"].double == b }!
            var result: [String: Double] = [:]
            for key in ["std_temp_c", "climb_speed_kias", "rate_fpm", "time_from_sl_min", "fuel_from_sl_gal", "distance_from_sl_nm"] {
                result[key] = Self.mix(altitude, a, b, first[key].double!, last[key].double!)
                steps.append(MathStep(title: name + " — " + key, formula: "POH cumulative sea-level table interpolation", value: Self.math(altitude, a, b, first[key].double!, last[key].double!)))
            }
            return result
        }
        let first = try at(start, name: "Start"), last = try at(target, name: "Target")
        let factor = 1 + 0.1 * max(oat - first["std_temp_c"]!, 0) / 10
        steps.append(MathStep(title: "Temperature factor", formula: "+10% per 10°C above standard at start", value: "1.0 + 0.1 × max(\(n(oat)) − (\(n(first["std_temp_c"]!))), 0.0) / 10.0 = \(n(factor * 100))%"))
        var values = ["pressure_alt_ft": start, "target_alt_ft": target, "oat_c": oat, "standard_oat_at_pressure_alt_c": first["std_temp_c"]!,
                      "climb_speed_kias_at_start": first["climb_speed_kias"]!, "climb_speed_kias_at_target": last["climb_speed_kias"]!,
                      "rate_of_climb_fpm_at_start": first["rate_fpm"]!, "rate_of_climb_fpm_at_target": last["rate_fpm"]!]
        for (key, output) in [("time_from_sl_min", "time_to_climb_min"), ("fuel_from_sl_gal", "fuel_used_gal_climb_only"), ("distance_from_sl_nm", "distance_to_climb_nm")] {
            let base = last[key]! - first[key]!, corrected = base * factor
            values[output] = corrected
            steps.append(MathStep(title: output, formula: "(Target cumulative − start cumulative) × temperature factor", value: "(\(n(last[key]!)) − \(n(first[key]!))) × \(n(factor * 100))% = \(n(corrected))"))
        }
        values["fuel_used_gal_with_start_taxi_takeoff"] = values["fuel_used_gal_climb_only"]! + 1.1
        steps.append(MathStep(title: "Start / taxi / takeoff fuel", formula: "Climb fuel + 1.1 US gal", value: "\(n(values["fuel_used_gal_climb_only"]!)) + 1.1 = \(n(values["fuel_used_gal_with_start_taxi_takeoff"]!)) US gal"))
        return Calculation(result: .numbers(values.mapValues(rounded1)), steps: steps)
    }
}
