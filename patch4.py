#!/usr/bin/env python3
"""Fork patch 4: trips list layout overhaul.

User verdict on v3 (2026-11-24 screenshot): "乱" — each drive was one
long bold line ("昨天 21:31 滨湖北路 → 体强路") that wrapped mid-name,
with the km value floating against the wrap, and the list merged
into the data rows above with no heading of its own.

v4: the trips block gets its own 「最近行程」 section title; drives
are grouped under day headers （今天 / 昨天 / M月D日）; each drive is
a two-line row — route on one line (nowrap, ellipsis, never wraps
mid-name) with start–end time + duration as a small grey meta line
under it, and the distance right-aligned in one nowrap figure.
Anchor/span-based like patch.py / patch2.py / patch3.py.
"""
PATH = "/home/hatch/workspace/model3-board-web/index.html"
src = open(PATH, encoding="utf-8").read()

# 1) Section title above the trips list.
OLD = """  <ul class="list" id="tripList"></ul>"""
NEW = """  <h2 class="sec-title">最近行程</h2>
  <ul class="list" id="tripList"></ul>"""
assert src.count(OLD) == 1, "tripList anchor"
src = src.replace(OLD, NEW)

# 2) Trip styles, inserted before the footer-notes CSS block.
OLD = """  /* ---------- 7) footer notes ---------- */"""
NEW = """  /* ---------- trips (v4 layout) ---------- */
  .trip-day{padding:18px 2px 0;font-size:13.5px;font-weight:600;color:var(--dim);letter-spacing:.05em}
  .trip{display:flex;align-items:center;gap:14px;padding:11px 0}
  .trip + .trip{border-top:1px solid var(--line)}
  .trip-main{flex:1;min-width:0}
  .trip-route{font-size:16.5px;font-weight:550;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .trip-meta{margin-top:3px;font-size:13px;color:var(--dim)}
  .trip-km{font-size:15.5px;font-weight:600;color:var(--text);white-space:nowrap}

  /* ---------- 7) footer notes ---------- */"""
assert src.count(OLD) == 1, "footer css anchor"
src = src.replace(OLD, NEW)

# 3) renderTrips rewrite (span replace up to fetchTrips).
NEW_JS = """  function dayLabel(iso){
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    var now = new Date();
    if (d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()) return '今天';
    var y = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
    if (d.getFullYear() === y.getFullYear() && d.getMonth() === y.getMonth() && d.getDate() === y.getDate()) return '昨天';
    return (d.getMonth() + 1) + '月' + d.getDate() + '日';
  }
  function renderTrips(data){
    var sumEl = document.getElementById('tripSummary');
    if (sumEl) sumEl.textContent = '今日 ' + data.today_count + ' 段 · ' + fmtKm(data.today_km) + ' km';
    var chgEl = document.getElementById('chargeSummary');
    if (chgEl) chgEl.textContent = data.charge_count > 0 ? ('共 ' + data.charge_count + ' 次') : '暂无记录';
    var list = document.getElementById('tripList');
    if (!list) return;
    list.innerHTML = '';
    function p2(n){ return (n < 10 ? '0' : '') + n; }
    function hm(iso){
      var d = new Date(iso);
      return isNaN(d.getTime()) ? '' : (p2(d.getHours()) + ':' + p2(d.getMinutes()));
    }
    var sumLi = document.createElement('li');
    sumLi.className = 'row';
    var sumNm = document.createElement('span');
    sumNm.className = 'name';
    sumNm.textContent = '累计行程';
    var sumVl = document.createElement('span');
    sumVl.className = 'val';
    sumVl.textContent = data.total_count + ' 段 · ' + fmtKm(data.total_km) + ' km';
    sumLi.appendChild(sumNm);
    sumLi.appendChild(sumVl);
    list.appendChild(sumLi);
    var drives = Array.isArray(data.drives) ? data.drives : [];
    if (!drives.length){
      var li0 = document.createElement('li');
      li0.className = 'row';
      var nm0 = document.createElement('span');
      nm0.className = 'name';
      nm0.textContent = '最近行程';
      var vl0 = document.createElement('span');
      vl0.className = 'val';
      vl0.textContent = '暂无记录';
      li0.appendChild(nm0);
      li0.appendChild(vl0);
      list.appendChild(li0);
      return;
    }
    var lastDay = null;
    drives.forEach(function(dv){
      var label = dayLabel(dv.start);
      if (label !== lastDay){
        lastDay = label;
        var hd = document.createElement('li');
        hd.className = 'trip-day';
        hd.textContent = label;
        list.appendChild(hd);
      }
      var li = document.createElement('li');
      li.className = 'trip';
      var main = document.createElement('div');
      main.className = 'trip-main';
      var route = document.createElement('div');
      route.className = 'trip-route';
      route.textContent = (dv.from_name || '未知地点') + ' → ' + (dv.to_name || '未知地点');
      var meta = document.createElement('div');
      meta.className = 'trip-meta';
      meta.textContent = hm(dv.start) + '–' + hm(dv.end) + ' · ' + dv.minutes + ' 分钟';
      main.appendChild(route);
      main.appendChild(meta);
      var km = document.createElement('span');
      km.className = 'trip-km';
      km.textContent = fmtKm(dv.km) + ' km';
      li.appendChild(main);
      li.appendChild(km);
      list.appendChild(li);
    });
  }
"""
start = src.index("  function renderTrips(data){")
end = src.index("  function fetchTrips(){", start)
src = src[:start] + NEW_JS + "\n" + src[end:]

open(PATH, "w", encoding="utf-8").write(src)
print("patch4 applied")
assert "dayLabel" in src and "trip-route" in src and "最近行程" in src
print("post-checks passed")
