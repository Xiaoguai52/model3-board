#!/usr/bin/env python3
"""Patch-4 verification: trips v4 layout (day groups, two-line rows).
Serves the fork in-process; intercepts every /cmd request; the real
channel is never touched. Saves a phone-viewport screenshot of the
trips section for visual review."""
import functools
import http.server
import json
import threading
from playwright.sync_api import sync_playwright

DIR = "/home/hatch/workspace/model3-board-web"
PORT = 8932
BASE = f"http://127.0.0.1:{PORT}/index.html"
KEY = "TESTKEY1234567890abcdefXYZ"
ASLEEP = {"ok": False, "http": 408, "tesla": {"response": None,
          "error": "vehicle unavailable: vehicle is offline or asleep"}}
# Times are UTC Z; Asia/Shanghai = UTC+8 (context timezone below).
TRIPS = {"ok": True, "http": 200, "tesla": {"response": {
    "total_count": 19, "total_km": 122.3, "today_count": 1,
    "today_km": 4.1, "charge_count": 0,
    "drives": [
        {"start": "2026-11-23T16:42:00Z", "end": "2026-11-23T16:58:00Z",
         "km": 4.1, "minutes": 16, "from_name": "云英路", "to_name": "南宁万丽酒店"},
        {"start": "2026-11-23T13:57:00Z", "end": "2026-11-23T14:04:00Z",
         "km": 2.3, "minutes": 7, "from_name": "体强路", "to_name": "坛泽路"},
        {"start": "2026-11-23T13:31:00Z", "end": "2026-11-23T13:53:00Z",
         "km": 15.0, "minutes": 22, "from_name": "滨湖北路", "to_name": "体强路"},
        {"start": "2026-11-23T13:05:00Z", "end": "2026-11-23T13:31:00Z",
         "km": 16.3, "minutes": 26, "from_name": "坛泽路", "to_name": "滨湖北路"},
        {"start": "2026-11-23T12:20:00Z", "end": "2026-11-23T12:26:00Z",
         "km": 2.2, "minutes": 6, "from_name": "打铁岭路", "to_name": "坛泽路"},
        {"start": "2026-11-23T10:12:00Z", "end": "2026-11-23T10:39:00Z",
         "km": 6.3, "minutes": 27, "from_name": "五象地下环路", "to_name": "打铁岭路"},
        {"start": "2026-11-23T01:15:00Z", "end": "2026-11-23T01:47:00Z",
         "km": 12.8, "minutes": 32,
         "from_name": "南宁市良庆区五象大道南宁万丽酒店",
         "to_name": "广西壮族自治区体育中心体育场"},
    ]}}}
CMD_OK = {"ok": True, "http": 200, "tesla": {"response": {"result": True, "reason": ""}}}

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIR)
server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
server.log_message = lambda *a: None
threading.Thread(target=server.serve_forever, daemon=True).start()

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 390, "height": 844},
                              timezone_id="Asia/Shanghai")
    page = ctx.new_page()
    calls = []
    def route_handler(route):
        body = {}
        try: body = json.loads(route.request.post_data or "{}")
        except Exception: pass
        cmd = body.get("command")
        calls.append(cmd)
        payload = TRIPS if cmd == "trips" else (ASLEEP if cmd == "state" else CMD_OK)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(payload))
    page.route("https://fleet.teslaxg.top/cmd", route_handler)
    page.goto(BASE + "#k=" + KEY, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    assert "trips" in calls, f"trips never fetched: {calls}"
    assert "wake_up" not in calls, f"car woken: {calls}"
    days = page.evaluate(
        "Array.from(document.querySelectorAll('#tripList .trip-day')).map("
        "function(e){ return e.textContent; })")
    assert days == ["今天", "昨天"], f"day headers wrong: {days}"
    trips = page.evaluate(
        "Array.from(document.querySelectorAll('#tripList .trip')).map("
        "function(r){ return r.querySelector('.trip-route').textContent + ' | ' + "
        "r.querySelector('.trip-meta').textContent + ' | ' + "
        "r.querySelector('.trip-km').textContent; })")
    assert len(trips) == 7, f"expected 7 trip rows, got: {trips}"
    assert trips[0].startswith("云英路 → 南宁万丽酒店"), trips[0]
    assert "00:42–00:58 · 16 分钟" in trips[0], trips[0]
    assert trips[2].startswith("滨湖北路 → 体强路") and "15.0 km" in trips[2], trips[2]
    assert "21:31–21:53 · 22 分钟" in trips[2], trips[2]
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 0, f"horizontal overflow: {overflow}px"
    route_wrap = page.evaluate(
        "var r = document.querySelectorAll('#tripList .trip-route')[6];"
        "({h: r.clientHeight, sh: r.scrollHeight, sw: r.scrollWidth, cw: r.clientWidth})")
    assert route_wrap["h"] <= 26 and route_wrap["sh"] == route_wrap["h"], \
        f"long route wrapped to multiple lines: {route_wrap}"

    page.evaluate("document.querySelectorAll('.sec-title')["
                  "document.querySelectorAll('.sec-title').length - 1"
                  "].scrollIntoView()")
    page.wait_for_timeout(600)
    page.screenshot(path=DIR + "/test4-trips.png")
    print("H ok: day groups, two-line rows, no wrap/overflow; screenshot saved")
    browser.close()
server.shutdown()
print("ALL PATCH-4 TESTS PASSED")
