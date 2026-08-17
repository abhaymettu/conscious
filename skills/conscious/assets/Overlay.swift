// conscious overlay — a full-screen 20s pause.
// Build: swiftc -O Overlay.swift -o overlay
// Run:   ./overlay "the line" ["attribution"]
//
// Swift owns only the window and the keyboard. Everything visible is pause.html
// next to this file, so the design can be edited without a recompile.

import AppKit
import WebKit

let HOLD: Double = 20.0
let FADE_IN: Double = 0.9
let FADE_OUT: Double = 0.9
let ESC_HOLD: Double = 3.0   // hold Esc this long to leave early
let SAFETY: Double = HOLD + 6 // never trap the screen if the page stalls

final class Controller: NSObject, NSApplicationDelegate, WKScriptMessageHandler {
    var windows: [NSWindow] = []
    var webs: [WKWebView] = []
    var timer: Timer?
    var escDown: Date?
    var closing = false
    let line: String, who: String, nth: String

    init(line: String, who: String, nth: String) {
        self.line = line
        self.who = who
        self.nth = nth
    }

    private func pageURL() -> URL {
        let dir = URL(fileURLWithPath: CommandLine.arguments[0])
            .resolvingSymlinksInPath().deletingLastPathComponent()
        var c = URLComponents(url: dir.appendingPathComponent("pause.html"),
                              resolvingAgainstBaseURL: false)!
        c.queryItems = [URLQueryItem(name: "line", value: line),
                        URLQueryItem(name: "who", value: who),
                        URLQueryItem(name: "n", value: nth)]
        return c.url!
    }

    func applicationDidFinishLaunching(_ n: Notification) {
        NSApp.setActivationPolicy(.accessory)

        let cfg = WKWebViewConfiguration()
        cfg.userContentController.add(self, name: "pause")
        cfg.suppressesIncrementalRendering = true

        let url = pageURL()
        let dir = url.deletingLastPathComponent()

        for screen in NSScreen.screens {
            let w = NSWindow(contentRect: screen.frame, styleMask: .borderless,
                             backing: .buffered, defer: false, screen: screen)
            w.level = .screenSaver
            w.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary, .ignoresCycle]
            w.isOpaque = false
            w.backgroundColor = .clear
            w.alphaValue = 0
            w.ignoresMouseEvents = true
            w.hidesOnDeactivate = false

            let web = WKWebView(frame: NSRect(origin: .zero, size: screen.frame.size), configuration: cfg)
            web.setValue(false, forKey: "drawsBackground")
            web.autoresizingMask = [.width, .height]
            web.loadFileURL(url, allowingReadAccessTo: dir)
            w.contentView = web
            webs.append(web)
            windows.append(w)
            w.orderFrontRegardless()
        }
        windows.first?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        // A beat before the fade so the first frame is the field, not a white flash.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            NSAnimationContext.runAnimationGroup { c in
                c.duration = FADE_IN
                self.windows.forEach { $0.animator().alphaValue = 1 }
            }
        }

        // Swallow every key while the pause holds, except a deliberate Esc hold.
        NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .keyUp, .flagsChanged]) { [weak self] e in
            self?.handle(e)
            return nil
        }

        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            guard let s = self, let d = s.escDown else { return }
            if Date().timeIntervalSince(d) >= ESC_HOLD { s.finish() }
        }
        RunLoop.main.add(timer!, forMode: .common)

        DispatchQueue.main.asyncAfter(deadline: .now() + SAFETY) { self.finish() }
    }

    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        if m.name == "pause" { finish() }
    }

    private func handle(_ e: NSEvent) {
        guard e.keyCode == 53 else { return }   // 53 = Escape
        if e.type == .keyDown {
            if escDown == nil { escDown = Date() }
        } else if e.type == .keyUp {
            escDown = nil
        }
    }

    private func finish() {
        guard !closing else { return }
        closing = true
        timer?.invalidate()
        webs.forEach { $0.evaluateJavaScript("window.leave && window.leave()") }
        NSAnimationContext.runAnimationGroup({ c in
            c.duration = FADE_OUT
            windows.forEach { $0.animator().alphaValue = 0 }
        }, completionHandler: { NSApp.terminate(nil) })
    }
}

let args = Array(CommandLine.arguments.dropFirst())
let app = NSApplication.shared
let ctl = Controller(line: args.first ?? "Be here now.",
                     who: args.count > 1 ? args[1] : "",
                     nth: args.count > 2 ? args[2] : "")
app.delegate = ctl
app.run()
