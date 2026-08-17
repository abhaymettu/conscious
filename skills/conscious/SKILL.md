---
name: conscious
description: Install, configure, tune, or troubleshoot "conscious" — a macOS daemon that takes over the full screen for an enforced twenty-second pause at random intervals, to interrupt autopilot and doomscrolling. Use when the user asks for a mindfulness or presence reminder, a forced break, a "stop and breathe" interrupt, a screen-takeover nudge, or names conscious directly. Also use to change its interval, hours, or lines, or when they say the pauses stopped firing.
---

# conscious

A full-screen pause that fires at random intervals and cannot be dismissed for
twenty seconds. Reading a good sentence does not make someone present; an
enforced gap between the stimulus and their next reflex action does. Everything
in the design serves that gap.

macOS only: it uses AppKit for a window that covers fullscreen apps, and launchd
to keep the daemon alive.

## Installing

Run the installer. It compiles the overlay, places the files, writes a launchd
plist with the user's real paths, and starts the daemon.

```bash
bash "$CLAUDE_PLUGIN_ROOT/skills/conscious/assets/install.sh"
```

It is safe to re-run: it upgrades in place and keeps the config, log, queue and
any lines the user has added.

Then interview them and write the config before firing anything — see
**Configuring** below. Do not fill it in from your own assumptions; the defaults
produce a tool that works, the interview produces one they keep.

Then fire one so they see what they just installed:

```bash
~/.local/bin/conscious now
```

Tell them it holds the screen for twenty seconds and that holding Esc for three
seconds leaves early. Do not fire one without saying so first — an unannounced
screen takeover reads as a crash.

If `swiftc` is missing, the installer says so: they need
`xcode-select --install`. Do not try to work around it; there is no other way to
get a window above fullscreen apps.

## What gets installed

| Path | What it is |
|---|---|
| `~/.local/bin/conscious` | the CLI and the daemon loop |
| `~/.conscious/overlay` | the compiled full-screen window |
| `~/.conscious/pause.html` | everything visible; edit it without recompiling |
| `~/.conscious/Overlay.swift` | the window host; recompile after editing |
| `~/.conscious/whispers.json` | the curated line pool, the floor under generation |
| `~/.conscious/config.json` | settings, created on first edit |
| `~/.conscious/log.jsonl` | one line per fire |
| `~/Library/LaunchAgents/com.conscious.daemon.plist` | keeps the daemon alive |

## Commands

```
conscious now [--line "..."]   fire once
conscious stats                pauses today, this week, all time
conscious config               current settings and where they live
conscious refill               top up the generated queue
```

## Configuring

Settings live in `~/.conscious/config.json`; anything absent falls back to the
default. The daemon re-reads it every cycle, so an edit takes effect without a
restart.

At install, interview the user rather than accepting the defaults silently. Ask
conversationally, a couple of questions at a time, and offer the default as the
easy answer. If your harness has a structured question tool, use it.

**Timing.**

| Key | Default | Ask | What to say |
|---|---|---|---|
| `min_gap_minutes` / `max_gap_minutes` | 20 / 60 | How often? | Random on purpose; a fixed schedule gets predicted and pre-dismissed. 20–60 interrupts real work sometimes. 45–120 is gentler, about six a day. If they insist on a fixed time, say that, then do it. |
| `wake_start_hour` / `wake_end_hour` | 9 / 23 | Between what hours? | 24-hour numbers. Later hours catch the doomscroll window. The end hour may wrap past midnight. |
| `bell` | true | A sound each time? | One soft chime. It conditions the ritual far faster than the visuals alone. |
| `away_channel` | `auto` | When the Mac is locked? | `auto` sends a macOS notification, or uses a `numen` command if one is on PATH. Any command taking the text as its first argument works. `off` means Mac only. |

**Content.** Every key here goes straight into the generation prompt. This is the
half people skip and the half that decides whether it lands.

| Key | Ask | What to say |
|---|---|---|
| `about` | What are you actually trying to interrupt? | The most valuable answer in the setup. Push past "being distracted" to the real shape: doomscrolling at 1am, seven hours of tabs with nothing to show, working through dinner without deciding to. Record their words, not your summary. |
| `themes` | Anything it should keep coming back to? | A short list of what they keep getting lost in. |
| `voice` | What should it sound like? | Default `"plain and quiet, not motivational, not clever"`. Some want blunt, some warm, some stoic and cold. Write a phrase, not a label. |
| `avoid` | Anything it must never do? | The one that saves the install. Common: guilt, productivity framing, telling them to get back to work, anything that sounds like an app. |
| `include_quotes` | Quotes, or only originals? | The pool mixes curated lines from Frankl, Seneca, Thich Nhat Hanh and others with originals in the same voice. `false` keeps only originals. |

After writing the config, run `conscious refill` so the first pause is already
personal rather than a default.

**`hold_seconds`** must also be changed in `pause.html` (the `HOLD` constant at
the top of the script block); the page owns the visible countdown and Swift owns
the safety timeout.

## Changing what it says

Two sources, in order:

1. **Generated**, if the `claude` CLI is on PATH. A queue of twenty lines is
   built ahead of time so a fire never waits on a model. Each batch is seeded
   with the hour and a rotating angle from `ANGLES` in the script, because
   without rotation a model converges on the same three sentences and the whole
   thing dies of semantic satiation inside a week.
2. **The curated pool** in `whispers.json`, drawn shuffle-bag style so nothing
   repeats until the pool is exhausted.

To change the voice, edit the prompt in `generate()`. To add lines by hand,
append `{"line": "...", "who": ""}` to `whispers.json` (`who` is an attribution,
empty for an original).

## Changing how it looks

`~/.conscious/pause.html` is the entire visible design and needs no recompile.
It is one file: a WebGL fragment shader for the field, then the type and the
marks over it.

The one idea worth preserving if you change anything: the field's temperature
rides the breath. It runs warm while the breath fills and cold while it empties,
so the colour is the instruction and no separate graphic is needed. `?b=1` and
`?b=0` on the URL pin the breath to either pole while tuning — serve the
directory over `python3 -m http.server` and open it in a browser rather than
firing the real overlay to iterate.

Do not add buttons, a skip control, or a countdown in seconds. The pause has no
affordances on purpose; the only exit is holding Esc, which is deliberate enough
that a reflex cannot trigger it.

## When it stops firing

Check in this order:

```bash
launchctl list | grep conscious      # is the daemon alive
tail -5 ~/.conscious/conscious.log   # it prints the next fire time
tail -5 ~/.conscious/conscious.err
conscious stats                      # did fires happen but land elsewhere
```

Most common causes, in order: the current time is outside the waking-hours
window (the log says `asleep for Nh`); the plist was never loaded; `swiftc`
output is stale after editing `Overlay.swift` and needs
`swiftc -O ~/.conscious/Overlay.swift -o ~/.conscious/overlay`.

## Uninstalling

```bash
launchctl unload ~/Library/LaunchAgents/com.conscious.daemon.plist
rm ~/Library/LaunchAgents/com.conscious.daemon.plist ~/.local/bin/conscious
rm -rf ~/.conscious
```
