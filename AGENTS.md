# Setting up conscious

You are reading this because someone handed you this repo and asked you to set it
up for them. This file is the whole job. It works with any coding agent; nothing
here is specific to one tool.

conscious is a macOS daemon that takes over the entire screen for twenty seconds
at random intervals. It cannot be clicked away. The point is the gap: reading a
good sentence does not make someone present, but an enforced pause between the
stimulus and their next reflex action does.

## Do this

**1. Check it can run here.** macOS only, and it needs `swiftc` and `python3`:

```bash
uname                        # must print Darwin
command -v swiftc python3
```

If `swiftc` is missing, tell them to run `xcode-select --install` and stop.
There is no workaround: only a native window can cover fullscreen apps.

**2. Install.**

```bash
bash skills/conscious/assets/install.sh
```

This compiles the overlay, installs the `conscious` command to `~/.local/bin`,
writes a launchd plist with their real paths, and starts the daemon. It is safe
to re-run and keeps any existing config, log and lines.

**3. Interview them, then write the config.** Do not skip this and do not fill it
in from your own assumptions. The defaults produce a tool that works; the
interview produces one they keep. A pause that fires at the wrong hour, or says
something generic, gets uninstalled inside a week.

Ask conversationally, a couple of questions at a time, and offer the default as
the easy answer so they can say "that's fine" and move on. If your harness has a
structured question tool, use it.

**Timing** — when it fires.

| Ask | Writes | Default | What to say |
|---|---|---|---|
| How often? | `min_gap_minutes`, `max_gap_minutes` | 20–60 | Random on purpose; a fixed schedule gets predicted and pre-dismissed. 20–60 interrupts real work sometimes. 45–120 is gentler, about six a day. |
| Between what hours? | `wake_start_hour`, `wake_end_hour` | 9–23 | 24-hour numbers. Later hours catch the doomscroll window, which is where autopilot lives hardest. `wake_end_hour` may wrap past midnight. |
| A sound each time? | `bell` | true | One soft chime. It conditions the ritual far faster than the visuals alone. |
| When the Mac is locked? | `away_channel` | `auto` | `auto` sends a macOS notification (or uses a `numen` command if they have one). Any command taking the text as its first argument works. `off` means Mac only. |

**Content** — what it says. This is the half people skip and the half that
decides whether the thing lands. Every key here goes straight into the
generation prompt.

| Ask | Writes | What to say |
|---|---|---|
| What are you actually trying to interrupt? | `about` | The most valuable answer in the whole setup. Push past "being distracted" to the real shape of it: doomscrolling at 1am, seven hours of tabs with nothing to show, working through dinner without deciding to. Write down their words, not your summary of them. |
| Anything it should keep coming back to? | `themes` | A short list. Whatever they keep getting lost in. |
| What should it sound like? | `voice` | Default is `"plain and quiet, not motivational, not clever"`. Some people want blunt, some want warm, some want stoic and cold. Ask which of those is closest and write it as a phrase, not a label. |
| Anything it must never do? | `avoid` | The one that saves the install. Common answers: guilt, productivity framing, telling them to get back to work, anything that sounds like an app. |
| Quotes, or only original lines? | `include_quotes` | The bundled pool mixes curated lines from Frankl, Seneca, Thich Nhat Hanh and others with originals in the same voice. `false` keeps only the originals. |

Write only what they actually gave you. Anything absent falls back to the
default, and the daemon re-reads the file every cycle, so edits take effect
without a restart.

```bash
cat > ~/.conscious/config.json <<'EOF'
{
  "min_gap_minutes": 45,
  "max_gap_minutes": 120,
  "wake_end_hour": 1,
  "about": "I lose whole evenings to tabs and then feel behind. It is worst after dinner.",
  "themes": ["doomscrolling", "working late without deciding to"],
  "voice": "blunt and warm, like a friend who is not impressed but is on my side",
  "avoid": ["guilt", "productivity framing", "telling me to get back to work"],
  "include_quotes": false
}
EOF
```

Then build their first queue with the new settings, so the very first pause is
already personal rather than a default:

```bash
~/.local/bin/conscious refill
```

They can change any of this later by editing that file or asking you to.

**4. Show them one, but warn them first.** Say that it will take over the whole
screen for twenty seconds and that holding Esc for three seconds leaves early.
An unannounced screen takeover reads as a crash.

```bash
~/.local/bin/conscious now
```

**5. Tell them these four commands and stop.**

```
conscious now       one right now
conscious stats     how many pauses today, this week, all time
conscious config    current settings and where they live
launchctl unload ~/Library/LaunchAgents/com.conscious.daemon.plist    stop it
```

## If they want to change what it says

Two sources. Generated lines, if the `claude` CLI is on their PATH: a queue of
twenty is built ahead of time so a fire never waits on a model. Otherwise the
curated pool in `~/.conscious/whispers.json`, drawn shuffle-bag style so nothing
repeats until it is exhausted.

To add their own, append to `whispers.json`:

```json
{ "line": "The screen was moving. The body was still.", "who": "" }
```

`who` is an attribution and is empty for an original. To change the voice of the
generated ones, edit the prompt in `generate()` in `~/.local/bin/conscious`.

## If they want to change how it looks

`~/.conscious/pause.html` is the entire visible design and needs no recompile.
One file: a WebGL fragment shader for the field, then the type over it.

Preserve one idea if you change anything: the field's temperature rides the
breath, warm while it fills and cold while it empties, so the colour is the
instruction and no separate graphic is needed. To iterate, serve the directory
and open it in a browser rather than firing the real overlay:

```bash
cd ~/.conscious && python3 -m http.server 8777
# then open http://127.0.0.1:8777/pause.html?line=Test%20line&n=4
# ?b=1 pins the breath to the warm pole, ?b=0 to the cold one
```

Do not add buttons, a skip control, or a visible seconds countdown. The pause has
no affordances on purpose. The only exit is holding Esc, which is deliberate
enough that a reflex cannot trigger it.

## If it stops firing

In this order:

```bash
launchctl list | grep conscious      # is the daemon alive
tail -5 ~/.conscious/conscious.log   # it prints the next fire time
tail -5 ~/.conscious/conscious.err
conscious stats                      # fires happening but landing elsewhere?
```

Most common cause by far: the current time is outside their waking-hours window,
and the log says `asleep for Nh`. That is correct behaviour, not a bug.
