import AppKit

// 仓库插件图标渲染器：解析 SVG 中的 rect / circle / path，按文档顺序绘制为 256x256 PNG。
//
// - path 命令支持 M/L/H/V/C/A/Z，绝对与相对（大小写）均可，支持隐式重复参数；
// - A 按 SVG 规范求圆心，用 kappa 近似（适合 ≤90° 的弧）；
// - 样式从 <g ...> 继承，元素自身属性可覆盖；支持 fill / stroke / stroke-width，
//   端点与拐角固定 round。SVG 中 rect / circle / path 需写成自闭合标签。
//
// 用法：swift scripts/render-icon.swift <输入.svg> <输出.png>
//
// 不要用 qlmanage 渲染：它在 48 尺寸下会把内容偏移到画布左上角，且圆角边缘
// 会混出白色弧线。本脚本输出精确 256x256，四角透明。

let args = CommandLine.arguments
guard args.count == 3 else {
    print("用法: render-icon.swift <输入.svg> <输出.png>")
    exit(2)
}

let svg = try String(contentsOfFile: args[1], encoding: .utf8)
let size = 256
let u = CGFloat(size) / 48
func fy(_ y: CGFloat) -> CGFloat { (48 - y) * u }
let kappa: CGFloat = 0.5523

struct Style {
    var fill: NSColor?
    var stroke: NSColor?
    var strokeWidth: CGFloat = 0
}

func parseColor(_ value: String) -> NSColor? {
    if value == "none" { return nil }
    let hex = value.hasPrefix("#") ? String(value.dropFirst()) : value
    var raw: UInt64 = 0
    guard Scanner(string: hex).scanHexInt64(&raw) else { return nil }
    return NSColor(srgbRed: CGFloat((raw >> 16) & 0xFF) / 255,
                   green: CGFloat((raw >> 8) & 0xFF) / 255,
                   blue: CGFloat(raw & 0xFF) / 255,
                   alpha: 1)
}

// 属性提取带词边界，避免 x="..." 误匹配 rx="..." 里的子串
func attrValue(_ attrs: String, _ name: String) -> String? {
    let pattern = "(?:^|\\s)" + name + "=\"([^\"]+)\""
    guard let re = try? NSRegularExpression(pattern: pattern) else { return nil }
    let full = NSRange(attrs.startIndex..., in: attrs)
    guard let m = re.firstMatch(in: attrs, range: full),
          let r = Range(m.range(at: 1), in: attrs) else { return nil }
    return String(attrs[r])
}

func attrNum(_ attrs: String, _ name: String) -> CGFloat? {
    guard let v = attrValue(attrs, name) else { return nil }
    return CGFloat(Double(v) ?? 0)
}

func overlay(_ base: Style, _ attrs: String) -> Style {
    var s = base
    if let f = attrValue(attrs, "fill") { s.fill = parseColor(f) }
    if let st = attrValue(attrs, "stroke") { s.stroke = parseColor(st) }
    if let sw = attrValue(attrs, "stroke-width"), let v = Double(sw) { s.strokeWidth = CGFloat(v) }
    return s
}

func paint(_ path: NSBezierPath, _ style: Style) {
    if let f = style.fill {
        f.setFill()
        path.fill()
    }
    if let st = style.stroke, style.strokeWidth > 0 {
        st.setStroke()
        path.lineWidth = style.strokeWidth * u
        path.stroke()
    }
}

func tokenize(_ d: String) -> [String] {
    var tokens: [String] = []
    var cur = ""
    for ch in d {
        if ch.isLetter {
            if !cur.isEmpty { tokens.append(cur); cur = "" }
            tokens.append(String(ch))
        } else if ch == " " || ch == "," || ch == "\n" || ch == "\t" {
            if !cur.isEmpty { tokens.append(cur); cur = "" }
        } else if ch == "-" || ch == "+" {
            if !cur.isEmpty { tokens.append(cur); cur = "" }
            cur.append(ch)
        } else {
            cur.append(ch)
        }
    }
    if !cur.isEmpty { tokens.append(cur) }
    return tokens
}

func drawPath(_ d: String, _ style: Style) {
    let tokens = tokenize(d)
    let path = NSBezierPath()
    var i = 0
    var cx: CGFloat = 0
    var cy: CGFloat = 0
    var sx: CGFloat = 0
    var sy: CGFloat = 0
    var last: Character = " "

    func take() -> CGFloat {
        guard i < tokens.count else { return 0 }
        let v = CGFloat(Double(tokens[i]) ?? 0)
        i += 1
        return v
    }

    while i < tokens.count {
        let token = tokens[i]
        var cmd: Character
        if token.count == 1, let c = token.first, c.isLetter {
            cmd = c
            last = c
            i += 1
        } else {
            cmd = last
            if cmd == "M" { cmd = "L" }
            if cmd == "m" { cmd = "l" }
        }
        let rel = cmd.isLowercase
        switch String(cmd).lowercased() {
        case "m":
            let x = take(), y = take()
            cx = rel ? cx + x : x
            cy = rel ? cy + y : y
            sx = cx
            sy = cy
            path.move(to: NSPoint(x: cx * u, y: fy(cy)))
        case "l":
            let x = take(), y = take()
            cx = rel ? cx + x : x
            cy = rel ? cy + y : y
            path.line(to: NSPoint(x: cx * u, y: fy(cy)))
        case "h":
            let x = take()
            cx = rel ? cx + x : x
            path.line(to: NSPoint(x: cx * u, y: fy(cy)))
        case "v":
            let y = take()
            cy = rel ? cy + y : y
            path.line(to: NSPoint(x: cx * u, y: fy(cy)))
        case "c":
            let x1 = take(), y1 = take()
            let x2 = take(), y2 = take()
            let x = take(), y = take()
            let p1 = rel ? CGPoint(x: cx + x1, y: cy + y1) : CGPoint(x: x1, y: y1)
            let p2 = rel ? CGPoint(x: cx + x2, y: cy + y2) : CGPoint(x: x2, y: y2)
            let end = rel ? CGPoint(x: cx + x, y: cy + y) : CGPoint(x: x, y: y)
            path.curve(to: NSPoint(x: end.x * u, y: fy(end.y)),
                       controlPoint1: NSPoint(x: p1.x * u, y: fy(p1.y)),
                       controlPoint2: NSPoint(x: p2.x * u, y: fy(p2.y)))
            cx = end.x
            cy = end.y
        case "a":
            let rx = take()
            _ = take()   // ry
            _ = take()   // x-axis-rotation
            _ = take()   // large-arc-flag
            let sweep = take()
            let x = take(), y = take()
            let ex = rel ? cx + x : x
            let ey = rel ? cy + y : y
            let dx = ex - cx, dy = ey - cy
            let half = sqrt(dx * dx + dy * dy) / 2
            let dist = sqrt(max(0, rx * rx - half * half))
            let len = sqrt(dx * dx + dy * dy)
            let perp = len > 0 ? CGPoint(x: -dy / len, y: dx / len) : .zero
            let mid = CGPoint(x: (cx + ex) / 2, y: (cy + ey) / 2)
            var center = CGPoint(x: mid.x + perp.x * dist, y: mid.y + perp.y * dist)
            // sweep=1 为 y 向下坐标系的顺时针，起点到终点的叉积应为正
            let cross = (cx - center.x) * (ey - center.y) - (cy - center.y) * (ex - center.x)
            if (cross > 0) != (sweep != 0) {
                center = CGPoint(x: mid.x - perp.x * dist, y: mid.y - perp.y * dist)
            }
            func tangent(_ px: CGFloat, _ py: CGFloat) -> CGPoint {
                let vx = px - center.x, vy = py - center.y
                // 顺时针：(x,y)→(-y,x)；逆时针：(x,y)→(y,-x)
                return sweep != 0 ? CGPoint(x: -vy, y: vx) : CGPoint(x: vy, y: -vx)
            }
            var t0 = tangent(cx, cy)
            var t1 = tangent(ex, ey)
            let l0 = sqrt(t0.x * t0.x + t0.y * t0.y)
            let l1 = sqrt(t1.x * t1.x + t1.y * t1.y)
            if l0 > 0 { t0.x /= l0; t0.y /= l0 }
            if l1 > 0 { t1.x /= l1; t1.y /= l1 }
            let c1 = CGPoint(x: cx + t0.x * kappa * rx, y: cy + t0.y * kappa * rx)
            let c2 = CGPoint(x: ex - t1.x * kappa * rx, y: ey - t1.y * kappa * rx)
            path.curve(to: NSPoint(x: ex * u, y: fy(ey)),
                       controlPoint1: NSPoint(x: c1.x * u, y: fy(c1.y)),
                       controlPoint2: NSPoint(x: c2.x * u, y: fy(c2.y)))
            cx = ex
            cy = ey
        case "z":
            path.line(to: NSPoint(x: sx * u, y: fy(sy)))
            cx = sx
            cy = sy
        default:
            i += 1
        }
    }
    path.close()
    paint(path, style)
}

// 样式作用域：<g> 块内的元素继承组样式，块外元素用 SVG 默认样式
let defaultStyle = Style(fill: NSColor.black, stroke: nil, strokeWidth: 0)
var groupStyle = defaultStyle
var groupBody: Range<String.Index>?
let gBlockRe = try NSRegularExpression(pattern: "<g\\s+([^>]*)>([\\s\\S]*?)</g>")
if let m = gBlockRe.firstMatch(in: svg, range: NSRange(svg.startIndex..., in: svg)),
   let attrsRange = Range(m.range(at: 1), in: svg),
   let bodyRange = Range(m.range(at: 2), in: svg) {
    groupStyle = overlay(defaultStyle, String(svg[attrsRange]))
    groupBody = bodyRange
}

guard let cs = CGColorSpace(name: CGColorSpace.sRGB),
      let ctx = CGContext(data: nil, width: size, height: size,
                          bitsPerComponent: 8, bytesPerRow: size * 4,
                          space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
    print("CGContext 创建失败")
    exit(1)
}
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
NSBezierPath.defaultLineCapStyle = .round
NSBezierPath.defaultLineJoinStyle = .round

// 按文档顺序绘制所有 rect / circle / path——必须尊重文档顺序，否则后画的背景会覆盖先画的图形
let elemRe = try NSRegularExpression(pattern: "<(rect|circle|path)\\s+([^>]*?)/>")
for m in elemRe.matches(in: svg, range: NSRange(svg.startIndex..., in: svg)) {
    guard let tr = Range(m.range(at: 1), in: svg),
          let ar = Range(m.range(at: 2), in: svg) else { continue }
    let tag = String(svg[tr])
    let attrs = String(svg[ar])
    let inGroup = groupBody.map { $0.contains(ar.lowerBound) } ?? false
    let style = overlay(inGroup ? groupStyle : defaultStyle, attrs)
    if tag == "path" {
        if let d = attrValue(attrs, "d") {
            drawPath(d, style)
        }
    } else if tag == "circle" {
        let cx = attrNum(attrs, "cx") ?? 0
        let cy = attrNum(attrs, "cy") ?? 0
        let r = attrNum(attrs, "r") ?? 0
        let rect = NSRect(x: (cx - r) * u, y: fy(cy + r), width: 2 * r * u, height: 2 * r * u)
        paint(NSBezierPath(ovalIn: rect), style)
    } else {
        let x = attrNum(attrs, "x") ?? 0
        let y = attrNum(attrs, "y") ?? 0
        guard let w = attrNum(attrs, "width"), let h = attrNum(attrs, "height") else { continue }
        let rx = attrNum(attrs, "rx") ?? 0
        let rect = NSRect(x: x * u, y: fy(y + h), width: w * u, height: h * u)
        paint(NSBezierPath(roundedRect: rect, xRadius: rx * u, yRadius: rx * u), style)
    }
}

NSGraphicsContext.restoreGraphicsState()

guard let cgOut = ctx.makeImage() else {
    print("CGImage 生成失败")
    exit(1)
}
let rep = NSBitmapImageRep(cgImage: cgOut)
guard let png = rep.representation(using: .png, properties: [:]) else {
    print("PNG 编码失败")
    exit(1)
}
do {
    try png.write(to: URL(fileURLWithPath: args[2]))
    print("已渲染 \(args[2])（\(size)x\(size)，来自 \(args[1])）")
} catch {
    print("写入失败: \(error)")
    exit(1)
}
