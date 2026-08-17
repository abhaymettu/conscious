# conscious

Everything stops for twenty seconds, at a time you cannot predict.

A macOS daemon that takes over the whole screen at random intervals with one
sentence and a breath, and will not let you click away. Reading a good line does
not make you present. The enforced gap between the stimulus and your next reflex
action does. Everything else here serves that gap.

The screen runs warm while your breath fills and cold while it empties, so the
colour is the instruction and there is nothing extra to read.

macOS only. It uses AppKit for a window that covers fullscreen apps, and launchd
to stay alive.

## Install

**Hand it to your coding agent.** Clone this and tell it to read `AGENTS.md`.
It will check the prerequisites, install, ask you four questions about timing,
write your config, and show you one. Works with any agent.

```
git clone https://github.com/abhaymettu/conscious
cd conscious && claude "set this up for me, read AGENTS.md"
```

**As a Claude Code plugin.**

```
/plugin marketplace add abhaymettu/conscious
/plugin install conscious
```

Then ask it to set conscious up.

**By hand.**

```bash
git clone https://github.com/abhaymettu/conscious
bash conscious/skills/conscious/assets/install.sh
conscious now
```

Needs `swiftc` (`xcode-select --install`) and `python3`.

## Use

```
conscious now       one right now
conscious stats     pauses today, this week, all time
conscious config    current settings and where they live
```

Hold Esc for three seconds to leave a pause early. It is deliberate enough that
a reflex cannot trigger it, and it means you are never trapped mid-call.

## Settings

`~/.conscious/config.json`. Anything absent falls back to the default, and the
daemon re-reads it every cycle.

```json
{
  "min_gap_minutes": 20,
  "max_gap_minutes": 60,
  "wake_start_hour": 9,
  "wake_end_hour": 23,
  "bell": true,
  "away_channel": "auto"
}
```

The interval is random on purpose. A fixed schedule gets predicted and
pre-dismissed within days.

`away_channel` is what happens when the screen is locked and the overlay would be
pointless: `auto` sends a macOS notification, or name any command that takes the
text as its first argument, or `off` for Mac only.

## What it says

If the `claude` CLI is on your PATH, lines are generated ahead of time into a
queue of twenty, each batch seeded with the hour and a rotating angle so the
model does not converge on the same three sentences. Otherwise it draws from a
curated pool, shuffle-bag style, so nothing repeats until the pool is exhausted.

Add your own to `~/.conscious/whispers.json`:

```json
{ "line": "What you are avoiding is smaller than the avoiding.", "who": "" }
```

The pool and the voice come from [numinous](https://www.abhaymettu.com).

## How it looks

`~/.conscious/pause.html` is the entire visible design, one file, no build step.
A WebGL fragment shader for the field and the type over it. Edit it and the next
pause picks it up.

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.conscious.daemon.plist
rm ~/Library/LaunchAgents/com.conscious.daemon.plist ~/.local/bin/conscious
rm -rf ~/.conscious
```
