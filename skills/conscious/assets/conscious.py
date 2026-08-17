#!/usr/bin/env python3
"""conscious — a random full-screen pause against autopilot.

  conscious now [--line "..."]   fire once, right now
  conscious daemon               loop forever, firing at random intervals
  conscious refill               top up the line queue
  conscious stats                how many pauses, and when
  conscious config               show the current settings and where they live

Everything stops for twenty seconds. That is the whole mechanism: reading a good
sentence does not make you present, but an enforced gap between the stimulus and
your next reflex does.

Lines are generated ahead of time into a queue so a fire never waits on a model.
When generation is unavailable a curated pool carries it, so a pause is never
missed for want of words.
"""
import json, os, random, re, shutil, subprocess, sys, time
from datetime import datetime, timedelta
from pathlib import Path

DIR = Path(os.environ.get("CONSCIOUS_HOME", Path.home() / ".conscious"))
QUEUE = DIR / "queue.json"
BAG = DIR / "bag.json"            # shuffle-bag state over the curated pool
POOL = DIR / "whispers.json"
LOG = DIR / "log.jsonl"
CONFIG = DIR / "config.json"
OVERLAY = DIR / "overlay"
BELL = "/System/Library/Sounds/Submarine.aiff"

DEFAULTS = {
    "min_gap_minutes": 20,
    "max_gap_minutes": 60,
    "wake_start_hour": 9,
    "wake_end_hour": 23,
    "hold_seconds": 20,
    "queue_target": 20,
    "queue_floor": 5,
    "model": "claude-sonnet-5",   # the fast tier is right for one-line generation
    "bell": True,
    "away_channel": "auto",       # auto | notify | <command> | off

    # Who this is for. Set by the agent at setup; everything below feeds the
    # generation prompt, so a line lands on this person and not on a generic one.
    "about": "",          # what they are actually trying to interrupt, in their words
    "voice": "plain and quiet, not motivational, not clever",
    "themes": [],         # what to circle back to: "doomscrolling", "overwork", ...
    "avoid": [],          # what a line must never do: "guilt", "productivity framing"
    "include_quotes": True,   # curated attributed lines, or originals only
}

# Rotated per batch. Without this a model converges on the same three sentences
# and the whole thing dies of semantic satiation inside a week.
ANGLES = [
    "the body: what it is doing right now that you have not noticed",
    "mortality: this hour is being spent, not saved",
    "avoidance: the thing you are circling instead of doing",
    "the sensory present: the room, the light, the sound in it",
    "joy: permission to want it now rather than after",
    "the cost of stimulus: what the last hour of input actually bought you",
    "agency: the gap between what happened and what you do next",
]


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    tmp.replace(path)  # atomic, so a crash mid-write never empties the queue


def cfg():
    return {**DEFAULTS, **load(CONFIG, {})}


# --- the pool -----------------------------------------------------------

def pool(c=None):
    p = load(POOL, [{"line": "Be here now.", "who": "Ram Dass"}])
    if c and not c["include_quotes"]:
        p = [w for w in p if not w.get("who")] or p
    return p


def from_bag():
    """Shuffle-bag draw: nothing repeats until the pool is exhausted."""
    p = pool(cfg())
    bag = load(BAG, [])
    if not bag:
        bag = list(range(len(p)))
        random.shuffle(bag)
    i = bag.pop()
    save(BAG, bag)
    return dict(p[i % len(p)], source="pool")


# --- generation ---------------------------------------------------------

def generate(n, angle, c):
    """Fresh lines in the same voice, or [] if no model is available."""
    claude = shutil.which("claude")
    if not claude:
        return []
    examples = [w["line"] for w in pool() if not w.get("who")]
    random.shuffle(examples)

    # Everything the user told the agent at setup, folded in. A line that knows
    # what this person is actually caught in beats a well-written general one.
    who = f"\nWho this is for: {c['about']}\n" if c["about"] else ""
    themes = (f"Come back to what they keep getting lost in: "
              f"{', '.join(c['themes'])}.\n") if c["themes"] else ""
    avoid = (f"Never: {'; '.join(c['avoid'])}.\n") if c["avoid"] else ""

    prompt = f"""Write {n} lines for a full-screen pause that interrupts someone mid-autopilot.

It is {datetime.now():%H:%M}. They have been feeding on input for the last hour without
noticing. The screen goes dark, everything stops for twenty seconds, and one of these
lines is all that is on it. Angle for this batch: {angle}.
{who}{themes}
Voice: {c['voice']}. Match the register of these:
{chr(10).join('- ' + e for e in examples[:8])}

Rules: one sentence each, second person, under fifteen words. No exclamation marks,
no questions that demand an answer, no em dashes. Nothing that asks them to do a
task. {avoid}Output only the lines, one per line, no numbering and no other text."""
    try:
        r = subprocess.run([claude, "-p", prompt, "--model", c["model"]],
                           capture_output=True, text=True, timeout=120)
    except Exception:
        return []
    out = []
    for raw in r.stdout.splitlines():
        s = raw.strip().lstrip("-*0123456789. ").strip().strip('"')
        if 10 < len(s) < 140 and "—" not in s:
            out.append({"line": s, "who": "", "source": "generated"})
    return out[:n]


def refill():
    c = cfg()
    q = load(QUEUE, [])
    need = c["queue_target"] - len(q)
    if need <= 0:
        return q
    angle = ANGLES[datetime.now().hour % len(ANGLES)]
    have = {x["line"] for x in q}
    q += [x for x in generate(need, angle, c) if x["line"] not in have]
    save(QUEUE, q)
    return q


# --- firing -------------------------------------------------------------

def screen_locked():
    """True when the screen is locked or the display has gone to sleep."""
    try:
        r = subprocess.run(["ioreg", "-n", "IODisplayWrangler", "-r", "-d", "1"],
                           capture_output=True, text=True, timeout=5)
        m = re.search(r'"CurrentPowerState"\s*=\s*(\d+)', r.stdout)
        if m and int(m.group(1)) < 4:
            return True
    except Exception:
        pass
    try:
        r = subprocess.run(
            ["python3", "-c",
             "import Quartz,sys;d=Quartz.CGSessionCopyCurrentDictionary() or {};"
             "sys.stdout.write(str(bool(d.get('CGSSessionScreenIsLocked'))))"],
            capture_output=True, text=True, timeout=5)
        return r.stdout.strip() == "True"
    except Exception:
        return False


def send_away(text, c):
    """Reach them when they are not at the desk, or return False if we cannot."""
    ch = c["away_channel"]
    if ch == "off":
        return False
    if ch == "auto":
        ch = "numen" if shutil.which("numen") else "notify"
    if ch == "notify":
        body = text.replace('"', "'")
        subprocess.run(["osascript", "-e",
                        f'display notification "{body}" with title "pause"'],
                       capture_output=True)
        return True
    if shutil.which(ch):
        subprocess.run([ch, text], capture_output=True)
        return True
    return False


def count_today():
    if not LOG.exists():
        return 0
    today = datetime.now().date().isoformat()
    return sum(1 for l in LOG.read_text().splitlines() if today in l[:30])


def fire(line=None):
    c = cfg()
    if line:
        item = {"line": line, "who": "", "source": "manual"}
    else:
        q = load(QUEUE, [])
        if q:
            item = q.pop(0)
            save(QUEUE, q)
        else:
            item = from_bag()

    nth = str(count_today() + 1)
    away = screen_locked()
    if away:
        text = item["line"] + (f"\n\n{item['who']}" if item.get("who") else "")
        away = send_away(text, c)
    if not away:
        if c["bell"] and Path(BELL).exists():
            subprocess.Popen(["afplay", "-v", "0.3", BELL],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([str(OVERLAY), item["line"], item.get("who", ""), nth])

    with LOG.open("a") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                            "line": item["line"], "source": item.get("source", "?"),
                            "surface": "away" if away else "overlay"}) + "\n")

    if not line and len(load(QUEUE, [])) < c["queue_floor"]:
        subprocess.Popen([sys.executable, __file__, "refill"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)


# --- daemon -------------------------------------------------------------

def sleep_until_awake(c):
    """Seconds to wait if we are outside waking hours, else 0."""
    now = datetime.now()
    start, end = c["wake_start_hour"], c["wake_end_hour"]
    inside = start <= now.hour < end if start < end else (now.hour >= start or now.hour < end)
    if inside:
        return 0
    nxt = now.replace(hour=start, minute=0, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


def daemon():
    c = cfg()
    print(f"conscious: up, {c['min_gap_minutes']}-{c['max_gap_minutes']} min, "
          f"{c['wake_start_hour']:02d}:00-{c['wake_end_hour']:02d}:00", flush=True)
    refill()
    while True:
        c = cfg()  # re-read so an edit takes effect without a restart
        wait = sleep_until_awake(c)
        if wait:
            print(f"asleep for {wait/3600:.1f}h", flush=True)
            time.sleep(wait)
            continue
        gap = random.randint(c["min_gap_minutes"], c["max_gap_minutes"]) * 60
        print(f"next at {(datetime.now()+timedelta(seconds=gap)):%H:%M}", flush=True)
        time.sleep(gap)
        if sleep_until_awake(cfg()):  # the window closed while we slept
            continue
        try:
            fire()
        except Exception as e:
            print(f"fire failed: {e}", flush=True)


def stats():
    rows = [json.loads(l) for l in LOG.read_text().splitlines()] if LOG.exists() else []
    today = datetime.now().date()
    d = sum(1 for r in rows if datetime.fromisoformat(r["ts"]).date() == today)
    w = sum(1 for r in rows if datetime.fromisoformat(r["ts"]).date() > today - timedelta(days=7))
    print(f"{d} pauses today, {w} this week, {len(rows)} all time")
    print(f"queue: {len(load(QUEUE, []))} lines, pool: {len(pool())}")
    for r in rows[-5:]:
        print(f"  {r['ts'][11:16]}  {r['line'][:64]}")


def main():
    DIR.mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "now"
    if cmd == "now":
        fire(sys.argv[sys.argv.index("--line") + 1] if "--line" in sys.argv else None)
    elif cmd == "daemon":
        daemon()
    elif cmd == "refill":
        print(f"queue: {len(refill())} lines")
    elif cmd == "stats":
        stats()
    elif cmd == "config":
        print(f"{CONFIG}\n" + json.dumps(cfg(), indent=2))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
