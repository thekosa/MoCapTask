# Tools Developer – take-home task

**Time box: 4 hours.** A working, well-checked subset beats an unfinished everything.

## Context
Our cleanup artists spend hours finding problems in motion-capture takes before they can fix them.
They want a tool that scans a take and tells them **what is wrong, where, and on which marker or joint**,
so they can jump straight to it.

## Data (`data/`)
| File | What it is |
|---|---|
| `take.c3d` | Optical markers of one performer, 30 s, 120 fps |
| `take.usd` | The skeleton solved from those markers (UsdSkel), same performer, same take |

That is all we tell you about the data. Part of the task is finding out what you're looking at.
The take contains a number of problems of different kinds. Some are easy to find, some are hard,
and some things that look like problems aren't.

## What to build
A command-line tool, preferably in Python (any libraries):

```
<your-tool> data/take.c3d data/take.usd -o out/
```

It writes:
1. **`out/report.json`**, machine-readable, in exactly this shape:
   ```json
   {
     "skel_to_c3d_offset_frames": 0,
     "events": [
       {"type": "spike", "targets": ["LFHD"], "start": 120, "end": 121, "confidence": 0.9, "note": "..."}
     ]
   }
   ```
   - `start`/`end` are inclusive, 0-based **C3D frame indices**, for marker and skeleton events alike.
   - `targets` are marker or joint names. `type` is your own vocabulary, e.g. `spike`, `gap`.
   - `skel_to_c3d_offset_frames`: the C3D frame that skeleton frame 0 corresponds to.
2. **A human-readable report** (HTML or Markdown) that an artist can act on. Plots welcome.

## What to hand in
A zip of your **git repository, including `.git`**. Commit as you go, the way you normally would. It should contain:
- the tool, with a README that says how to run it
- tests
- `out/` produced from the provided data
- **`NOTES.md`** (short is fine):
  - what you found out about the data (units, axes, timing, conventions)
  - how each detector works, and **how you verified it** on data you control
  - what you deliberately left out, the known false positives/negatives, and what you'd do next

## How we evaluate
- How many real problems you find, and how few false alarms: an artist loses time on every false alarm.
- How you checked your own work.
- Code an engineer here could pick up and extend.
- Your reasoning in `NOTES.md`.

After you hand in, we'd like to discuss your results with you on a call.
