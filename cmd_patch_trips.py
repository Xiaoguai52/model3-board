#!/usr/bin/env python3
"""Server patch: add a read-only 'trips' command to cmd_server.py.

The command answers from TeslaMate's Postgres (recent drives +
totals) and never touches Tesla — no token use, no car wake.
Run on the server as ubuntu. Backs up first; restores on failure.
"""
import py_compile
import shutil
import sys

PATH = "/home/ubuntu/tesla-fleet/cmd_server.py"
src = open(PATH, encoding="utf-8").read()

if "_trips" in src:
    print("trips already present, nothing to do")
    sys.exit(0)

HELPER = '''
TRIPS_SQL = """
SELECT json_build_object(
  'total_count', (SELECT count(*) FROM drives),
  'total_km', (SELECT round(coalesce(sum(distance), 0)::numeric, 1) FROM drives),
  'today_count', (SELECT count(*) FROM drives WHERE (start_date + interval '8 hours')::date = ((now() AT TIME ZONE 'UTC') + interval '8 hours')::date),
  'today_km', (SELECT round(coalesce(sum(distance), 0)::numeric, 1) FROM drives WHERE (start_date + interval '8 hours')::date = ((now() AT TIME ZONE 'UTC') + interval '8 hours')::date),
  'charge_count', (SELECT count(*) FROM charging_processes),
  'drives', (SELECT coalesce(json_agg(x), '[]'::json) FROM (
      SELECT to_char(d.start_date, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS start,
             to_char(d.end_date, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS "end",
             round(d.distance::numeric, 1) AS km,
             d.duration_min AS minutes,
             split_part(coalesce(sa.display_name, ''), ',', 1) AS from_name,
             split_part(coalesce(ea.display_name, ''), ',', 1) AS to_name
      FROM drives d
      LEFT JOIN addresses sa ON sa.id = d.start_address_id
      LEFT JOIN addresses ea ON ea.id = d.end_address_id
      ORDER BY d.start_date DESC LIMIT 10) x)
)::text;
"""

def _trips():
    # Trip history lives in TeslaMate's database on this server; it
    # has nothing to do with the car, so this command never touches
    # Tesla and never wakes anything. The DB is only reachable from
    # inside its container, hence docker exec with the container's
    # own environment for credentials.
    try:
        proc = subprocess.run(
            ["sudo", "-n", "docker", "exec", "-i", "teslamate-database-1",
             "sh", "-c", "PGPASSWORD=$POSTGRES_PASSWORD psql -U $POSTGRES_USER -d $POSTGRES_DB -At"],
            input=TRIPS_SQL, capture_output=True, text=True, timeout=25)
        lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
        if proc.returncode != 0 or not lines:
            return False, 502, {"error": "trips unavailable"}
        return True, 200, {"response": json.loads(lines[-1])}
    except Exception:
        return False, 502, {"error": "trips unavailable"}

'''

ANCHOR_DEF = "def forward(command, params=None):"
assert src.count(ANCHOR_DEF) == 1, "forward def anchor missing"
src = src.replace(ANCHOR_DEF, HELPER.lstrip("\n") + ANCHOR_DEF)

ANCHOR_HEAD = 'def forward(command, params=None):\n    if command == "state":'
assert src.count(ANCHOR_HEAD) == 1, "forward head anchor missing"
src = src.replace(
    ANCHOR_HEAD,
    'def forward(command, params=None):\n    if command == "trips":\n        return _trips()\n    if command == "state":')

shutil.copy2(PATH, PATH + ".bak-trips")
open(PATH, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(PATH, doraise=True)
except Exception as exc:
    shutil.copy2(PATH + ".bak-trips", PATH)
    print("compile failed, backup restored:", exc)
    sys.exit(1)
print("trips patch applied and compiles")
