import SwiftUI

@MainActor
struct WeightBalanceView: View {
    @EnvironmentObject var store: NativeStore
    @State private var loads = ["pilot_weight_lbs": "180", "front_passenger_weight_lbs": "205", "rear_left_weight_lbs": "205", "rear_right_weight_lbs": "0", "baggage1_weight_lbs": "0", "baggage2_weight_lbs": "0", "fuel_gal": "25", "taxi_fuel_gal": "1", "trip_fuel_gal": "12"]
    @State private var calculation: Calculation?
    @State private var error: String?
    @State private var token = UUID()
    @FocusState private var keyboard: Bool
    private var wb: J { store.displayProfile["wb"] }
    private func binding(_ key: String) -> Binding<String> {
        Binding(get: { loads[key] ?? "" }, set: { loads[key] = $0; calculation = nil; error = nil })
    }
    var body: some View {
        ScrollViewReader { proxy in
            Form {
                Section { AircraftSelection() }
                emptySection
                stationsSection
                fuelSection
                Section {
                    Button {
                        keyboard = false; endNativeEditing()
                        do {
                            var form = J.object(loads.mapValues(J.string))
                            for station in wb["stations"].array where !station["enabled"].flag { form[station["key"].text] = .number(0) }
                            calculation = try store.engine?.calculate("weight-balance", form: form, profile: store.activeProfile)
                            error = nil; token = UUID()
                        } catch { self.error = error.localizedDescription; calculation = nil }
                    } label: { Label(store.label("Calculate W&B", "计算重量与重心"), systemImage: "equal.square") }
                    .accessibilityIdentifier("calculate-wb")
                    .disabled(store.activeProfile == nil)
                }
                if let error { Section { Text(error).foregroundStyle(.red) } }
                if let calculation {
                    WBEnvelopeSection(calculation: calculation).id("wb-result")
                    Section("CG envelope / 重心包线") {
                        CGPlot(plot: calculation.result["plot"]).frame(height: 310)
                            .accessibilityElement().accessibilityLabel("CG envelope").accessibilityIdentifier("cg-plot")
                    }
                    Section(store.label("Calculation table", "计算表")) { LoadingTable(rows: calculation.result["rows"].array) }
                    StepsSection(steps: calculation.steps)
                }
            }.onChange(of: token) { _, _ in withAnimation { proxy.scrollTo("wb-result", anchor: .top) } }
        }
        .navigationTitle("Weight & Balance")
        .toolbar { ToolbarItemGroup(placement: .keyboard) { Spacer(); Button(store.label("Done", "完成")) { keyboard = false; endNativeEditing() } } }
        .onChange(of: store.activeID) { _, _ in calculation = nil; error = nil }
        .onChange(of: store.activeProfile) { _, _ in calculation = nil; error = nil }
    }
    private func fixed(_ key: String, unit: String) -> String { wb[key].double.map { n($0) + " " + unit } ?? "—" }
    private var emptySection: some View {
        Section(store.label("Empty aircraft", "空机数据")) {
            LabeledContent(fieldName("empty_weight_lb", chinese: store.chinese), value: fixed("empty_weight_lb", unit: "lb"))
            LabeledContent(fieldName("empty_moment_lb_in", chinese: store.chinese), value: fixed("empty_moment_lb_in", unit: "lb-in"))
            if let weight = wb["empty_weight_lb"].double, let moment = wb["empty_moment_lb_in"].double, weight > 0 {
                LabeledContent(store.label("Empty CG", "空机重心"), value: n(moment / weight) + " in")
            }
        }
    }
    private var stationsSection: some View {
        Section(store.label("Occupants and baggage", "乘员与行李")) {
            ForEach(Array(wb["stations"].array.enumerated()), id: \.offset) { _, station in
                VStack(alignment: .leading, spacing: 4) {
                    NumberRow(title: station["label"].text, unit: "lb", id: station["key"].text,
                              text: station["enabled"].flag ? binding(station["key"].text) : .constant("0"))
                        .disabled(!station["enabled"].flag).focused($keyboard)
                    Text(store.label("Arm: ", "力臂：") + (station["arm_in"].double.map(n) ?? "—") + " in")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
        }
    }
    private var fuelSection: some View {
        Section(store.label("Fuel", "燃油")) {
            NumberRow(title: store.label("Fuel on board", "机上燃油"), unit: "US gal", id: "fuel_gal", text: binding("fuel_gal")).focused($keyboard)
            NumberRow(title: store.label("Taxi fuel", "滑行用油"), unit: "US gal", id: "taxi_fuel_gal", text: binding("taxi_fuel_gal")).focused($keyboard)
            NumberRow(title: store.label("Trip fuel", "航程用油"), unit: "US gal", id: "trip_fuel_gal", text: binding("trip_fuel_gal")).focused($keyboard)
            LabeledContent(fieldName("fuel_arm_in", chinese: store.chinese), value: fixed("fuel_arm_in", unit: "in"))
            LabeledContent(fieldName("fuel_density_lb_gal", chinese: store.chinese), value: fixed("fuel_density_lb_gal", unit: "lb/US gal"))
        }
    }
}

@MainActor
struct WBEnvelopeSection: View {
    @EnvironmentObject var store: NativeStore
    var calculation: Calculation
    var body: some View {
        Section(store.label("Envelope check", "包线检查")) {
            ForEach(Array(calculation.result["envelope"].array.enumerated()), id: \.offset) { index, phase in
                WBPhaseRow(phase: phase, explanation: calculation.result["explanations"][index])
            }
        }
    }
}

struct WBPhaseRow: View {
    var phase: J
    var explanation: J
    private var valid: Bool { phase["status"].text == "OK" }
    var body: some View {
        DisclosureGroup {
            Text(phase["message"].text).foregroundStyle(valid ? Color.secondary : Color.red)
            Text(explanation["lines"].array.map(\.text).joined(separator: "\n"))
                .font(.system(.body, design: .monospaced)).textSelection(.enabled)
        } label: {
            HStack {
                Image(systemName: valid ? "checkmark.circle.fill" : "exclamationmark.triangle.fill").foregroundStyle(valid ? Color.green : Color.red)
                Text(phase["phase"].text)
                Spacer()
                Text(n(phase["weight"].double!) + " lb / " + n(phase["cg"].double!) + " in").monospacedDigit().font(.subheadline)
            }
        }
        .accessibilityIdentifier("wb-phase-" + phase["phase"].text)
    }
}

struct LoadingTable: View {
    var rows: [J]
    var body: some View {
        ScrollView(.horizontal) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text("Item").frame(width: 135, alignment: .leading)
                    ForEach(["Arm (in)", "Weight (lb)", "Moment (lb-in)", "CG (in)"], id: \.self) { Text($0).frame(width: 110, alignment: .trailing) }
                }.font(.caption).foregroundStyle(.secondary)
                ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                    Divider()
                    HStack {
                        Text(row["item"].text).frame(width: 135, alignment: .leading)
                        ForEach(["arm", "weight", "moment", "cg"], id: \.self) { key in
                            Text(row[key].double.map(n) ?? "—").frame(width: 110, alignment: .trailing).monospacedDigit()
                        }
                    }.font(.subheadline).fontWeight(row["kind"].text == "total" ? .bold : .regular)
                }
            }.padding(.vertical, 4)
        }
    }
}

struct CGPlot: View {
    var plot: J
    var body: some View {
        Canvas { context, size in
            let envelope = plot["envelope"].array, points = plot["points"].array
            let all = envelope + points
            guard !envelope.isEmpty else { return }
            let minX = (all.compactMap { $0["cg"].double }.min() ?? 30) - 1
            let maxX = (all.compactMap { $0["cg"].double }.max() ?? 50) + 1
            let minY = (all.compactMap { $0["weight"].double }.min() ?? 0) * 0.95
            let maxY = (all.compactMap { $0["weight"].double }.max() ?? 2500) * 1.05
            let rect = CGRect(x: 48, y: 20, width: max(size.width - 66, 1), height: max(size.height - 58, 1))
            func point(_ row: J) -> CGPoint {
                CGPoint(x: rect.minX + (row["cg"].double! - minX) / max(maxX - minX, 1) * rect.width,
                        y: rect.maxY - (row["weight"].double! - minY) / max(maxY - minY, 1) * rect.height)
            }
            for index in 0...4 {
                let fraction = Double(index) / 4, y = rect.maxY - fraction * rect.height
                var line = Path(); line.move(to: CGPoint(x: rect.minX, y: y)); line.addLine(to: CGPoint(x: rect.maxX, y: y))
                context.stroke(line, with: .color(.gray.opacity(0.2)), lineWidth: 1)
                context.draw(Text(n(minY + fraction * (maxY - minY))).font(.system(size: 10)), at: CGPoint(x: rect.minX - 5, y: y), anchor: .trailing)
                context.draw(Text(n(minX + fraction * (maxX - minX))).font(.system(size: 10)), at: CGPoint(x: rect.minX + fraction * rect.width, y: rect.maxY + 14))
            }
            var boundary = Path(); boundary.move(to: point(envelope[0]))
            for row in envelope.dropFirst() { boundary.addLine(to: point(row)) }; boundary.closeSubpath()
            context.fill(boundary, with: .color(.teal.opacity(0.12))); context.stroke(boundary, with: .color(.teal), lineWidth: 2)
            if let first = points.first {
                var line = Path(); line.move(to: point(first)); for row in points.dropFirst() { line.addLine(to: point(row)) }
                context.stroke(line, with: .color(.primary), style: StrokeStyle(lineWidth: 1.5, dash: [4, 3]))
            }
            var labelPositions: [Int: Double] = [:]
            var nextLabelY = rect.minY + 10
            for index in points.indices.sorted(by: { point(points[$0]).y < point(points[$1]).y }) {
                let y = max(point(points[index]).y, nextLabelY)
                labelPositions[index] = y
                nextLabelY = y + 18
            }
            let overflow = max((labelPositions.values.max() ?? rect.maxY) - rect.maxY + 8, 0)
            for (index, row) in points.enumerated() {
                let location = point(row)
                context.fill(Path(ellipseIn: CGRect(x: location.x - 4, y: location.y - 4, width: 8, height: 8)), with: .color(row["status"].text == "OK" ? .green : .red))
                let label = CGPoint(x: min(location.x + 14, rect.maxX - 75), y: labelPositions[index]! - overflow)
                var leader = Path(); leader.move(to: location); leader.addLine(to: CGPoint(x: label.x - 3, y: label.y))
                context.stroke(leader, with: .color(.secondary.opacity(0.6)), lineWidth: 0.7)
                context.draw(Text("\(index + 1). " + row["label"].text).font(.system(size: 10)), at: label, anchor: .leading)
            }
            context.draw(Text("CG (in)").font(.caption), at: CGPoint(x: rect.midX, y: size.height - 5), anchor: .bottom)
            context.draw(Text("lb").font(.caption), at: CGPoint(x: 14, y: 7))
        }.accessibilityLabel("CG envelope with ZFW, ramp, takeoff and landing points")
    }
}
