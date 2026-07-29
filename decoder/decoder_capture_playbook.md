# Sundance Panel96 Capture and Decode Playbook

## Goal

Produce recordings that can be decoded reliably by the current Panel96 timeline decoder.

## What Was Verified

### Working recordings

- `messungen/29.9_12-45.sr` (8 MHz): valid frames extracted, timeline runs printed.
- `messungen/12-00_8-00.sr` (8 MHz): valid frames extracted, timeline runs printed.

### Not working with current path

- `messungen/alt/live_soll35_ist31-5_20260725_194735.sr` (1 MHz): `frames=0`, no valid frames extracted.
- `messungen/alt/live_30-36_20260725_185258.sr` (1 MHz): `frames=0`, no valid frames extracted.

## Sampling Rate Recommendation

- Preferred: **24 MHz**
- Good fallback: **8 MHz**
- Avoid for this decoder path: **1 MHz**

### Sample Count Quick Reference

- Formula: `samples = sample_rate_hz * duration_s`
- For 24 MHz and 20 s:
	- `24,000,000 * 20 = 480,000,000`
	- Result: **480,000,000 samples per channel**

Reason: the current `panel96_number_timeline.py` extraction depends on stable 96-bit frame structure that is much more reliable at higher sample rates.

## Probe and Signal Setup

Keep wiring and channel mapping stable across all captures:

- Clock: `D7`
- Latch/CS: `D6`
- Data primary: `D4`
- Data secondary (recommended to record too): `D5`

## Recording Checklist

1. Use 24 MHz when possible.
2. Capture 8 to 20 seconds per file.
3. Include clear stable phases per shown value (temperature/time).
4. Avoid rapid switching during a single short capture.
5. Keep acquisition settings identical across the measurement session.

## Decode Commands

Run all three views for each new file:

```bash
/Users/lukas/sundance/.venv/bin/python decoder/panel96_number_timeline.py messungen/FILE.sr --reference-dir messungen --mode all
/Users/lukas/sundance/.venv/bin/python decoder/panel96_number_timeline.py messungen/FILE.sr --reference-dir messungen --mode temp
/Users/lukas/sundance/.venv/bin/python decoder/panel96_number_timeline.py messungen/FILE.sr --reference-dir messungen --mode time
```

## Minimal Validation Criteria

A capture is considered usable when:

- output shows `frames > 0`
- output contains `runs:` with at least one stable run
- confidence values are consistently high for repeated segments

## Troubleshooting

If output says `No valid frames extracted.`:

1. Re-record at 24 MHz.
2. Confirm channel assignments (`D7`, `D6`, `D4`, optional `D5`).
3. Check probe contact quality and ground reference.
4. Retry with a capture containing longer stable display periods.

## Suggested File Naming

Use explicit semantic names for references, for example:

- `29.9_12-45_24mhz_YYYYMMDD_HHMMSS.sr`
- `12-00_8-00_24mhz_YYYYMMDD_HHMMSS.sr`
- `blind_24mhz_YYYYMMDD_HHMMSS.sr`

## PulseView Custom Decoder Integration

You can load the custom decoder package from this workspace:

- Decoder path in workspace: `sigrok-decoders/panel96`
- Required files:
	- `sigrok-decoders/panel96/__init__.py`
	- `sigrok-decoders/panel96/pd.py`

### Decoder Purpose

The custom decoder extracts latch-delimited frames on the panel bus and
annotates frame length and payload.

Default assumptions in `panel96` decoder:

- `CLK` channel: D7
- `LATCH` channel: D6
- `DATA` channel: D4
- expected symbols per frame: 96
- sample clock edge: rising
- frame boundary edge: rising

### Start PulseView With Custom Decoder Path (macOS)

PulseView started from Finder may not inherit shell environment variables.
Start it from Terminal with decoder path exported:

```bash
cd /Users/lukas/sundance
export SIGROKDECODE_DIR="$PWD/sigrok-decoders"
pulseview
```

If your installation uses a different executable name, use that executable
with the same environment variable.

### In PulseView

1. Open a recording.
2. Add protocol decoder `Panel96`.
3. Map channels:
	 - `CLK -> D7`
	 - `LATCH -> D6`
	 - `DATA -> D4`
	 - optional `DATA2 -> D5`
4. Keep defaults first (`expected_symbols=96`, rising/rising).
5. If needed, set `strict_length=no` to inspect non-perfect captures.

### Two-Stage Decoder Chain (Values In PulseView)

To display semantic values (for known profiles) directly in PulseView, stack a
second decoder on top of `Panel96`:

1. Add `Panel96` (stage 1) with channel mapping (`CLK=D7`, `LATCH=D6`,
	 `DATA=D4`).
2. Add `Panel96 Values` (stage 2) and select profile:
	 - `12-00_8-00`
	 - `29.9_12-45`
3. Ensure stage 2 uses stage 1 output as input (decoder stack, not parallel).

CLI equivalent for stacked decode:

```bash
SIGROKDECODE_DIR=/Applications/PulseView.app/Contents/share/libsigrokdecode/decoders \
sigrok-cli -i messungen/12-00_8-00.sr \
	-P panel96:clk=D7:latch=D6:data=D4,panel96_values:profile=12-00_8-00 \
	-A panel96_values
```

Manual mapping is also supported in stage 2 using:

- option `mapping` with format `HEX=LABEL,HEX=LABEL`
- example: `0x00007FFFFBF7FFFF40C0A4F9=12:00`

### Auto-Learn Mode (No Profile Required)

`Panel96 Values` can learn stable unknown signatures and assign temporary
labels (`AUTO1`, `AUTO2`, ...).

Recommended settings:

1. `profile = none`
2. `phase_aware = yes`
3. `semantic_guess = yes`
4. `semantic_anchors = LABEL=HEX|HEX;LABEL2=HEX|HEX` (optional calibration)
4. `guess_max_distance = 10`
5. `autolearn = yes`
6. `autolearn_min_count = 12` (or higher for stricter learning)

Behavior:

1. Unknown signatures are first shown as `UNKNOWN(n)` where `n` is seen count.
2. With `phase_aware=yes`, alternating scan phases are grouped into one state.
3. With `semantic_guess=yes`, known states can be shown directly (for example
	`12:00`, `8:00`, `29.9C`, `12:45`) even with `profile=none`.
4. Unknown states are promoted to `AUTO<n>` after `autolearn_min_count`.
5. Signature row shows pair mapping hints like `SIG_A|SIG_B=AUTO1`.

### Semantic Anchors (Calibration Without Built-in Value Templates)

Use `semantic_anchors` to define your own semantic labels from measured
phase-pairs. Format:

- `LABEL=HEX|HEX;LABEL2=HEX|HEX`

Examples:

- `T1200=0x...A4F9|0x...5B06;T0800=0x...00FF|0x...FF00`

Notes:

1. In PulseView UI labels may include `:`.
2. In `sigrok-cli -P ...` avoid `:` inside labels because option parsing uses
	`:` separators.

### Anchor Export Helper

Generate anchor candidates from a recording:

```bash
/Users/lukas/sundance/.venv/bin/python decoder/export_semantic_anchors.py \
	messungen/12-00_8-00.sr --min-pair-count 20 --label-prefix VAL
```

Generate compact anchors across all recordings (including subfolders like
`messungen/alt` and `messungen/boot`) by passing the root directory:

```bash
/Users/lukas/sundance/.venv/bin/python decoder/export_semantic_anchors.py \
	messungen --min-pair-count 50 --cluster-distance 8 --max-states 12 --label-prefix ST
```

Notes:

1. Directory inputs are scanned recursively for `*.sr` files.
2. `--cluster-distance` merges near-identical phase-pairs into fewer states.
3. Prefer one anchor set per capture family when global set produces many
	`UNKNOWN` labels.

The tool prints:

1. dominant signatures and counts
2. selected phase-pairs (`state1`, `state2`, ...)
3. ready-to-paste `semantic_anchors` string

CLI example:

```bash
SIGROKDECODE_DIR=/Applications/PulseView.app/Contents/share/libsigrokdecode/decoders \
sigrok-cli -i messungen/12-00_8-00.sr \
	-P panel96:clk=D7:latch=D6:data=D4,panel96_values:profile=none:autolearn=yes:phase_aware=yes:semantic_guess=yes:autolearn_min_count=12 \
	-A panel96_values
```

Important option values for `panel96_values` in CLI:

1. Use `yes`/`no` (not `1`/`0`) for boolean-like options.
2. Example: `autolearn=no:phase_aware=yes:semantic_guess=yes`.

### Current Compact Anchor Presets (Verified)

Global set (all files under `messungen/**`):

```text
ST1=0x000004040060393FBF4F|0xFFFFFBFBFFFFC6C040B0;ST2=0x000006040062397D864F|0xFFFFF9FBFFFDC68279B0;ST3=0x0000040400603906EF5B|0xFFFFFBFBFFFFC6F910A4;ST4=0x00000400006000380671|0xFFFFFBFFFFFFFFC7F98E;ST5=0x000000040064396FEF5B|0xFFFFFFFBFFFBC69010A4;ST6=0x400800000064ED665B06|0xBFF7FFFFFFFB1299A4F9;ST7=0x00000400006000003E00|0xFFFFFBFFFFFFFFFFC1FF;ST8=0x00000400806039500439|0xFFFFFBFF7FFFC6AFFBC6;ST9=0x7FFFFBF7FFFF40C0A4F9|0x800004080060BF3F5B06;ST10=0x000004040060395BEF5B|0xFFFFFBFBFFFFC6A410A4;ST11=0x0000000000607706DB00|0xFFFFFFFFFFFF11F249FF;ST12=0x0000040400605B7DB00F|0xFFFFFBFBFFFFA4824FF0;ST13=0x000004100060BF3FFF00|0xFFFFFBEFFFFF40C000FF;ST14=0x0000080800C072CD0C9F|0xFFFFFBFBFFFFC69979B0;ST15=0xFFFFF9FBFFFDC68279B0|0xFFFFF9FBFFFDC682F9B0;ST16=0xFFFFFBFBFFFFC6C040B0|0xFFFFFBFBFFFFC6C0C0B0
```

ALT pool set (`messungen/alt/pool_26-27..29-30`):

```text
ALT1=0x000004050060393FEF5B|0xFFFFF7F5FFFF8D802149;ALT2=0x0000080A00C0727F7E9F|0xFFFFFBFAFFFFC6C040B0;ALT3=0x00000C0F00C07B7FFFFF|0xFFFFFBFAFFFFC6C000A4;ALT4=0x0000080800C072DBCC9F|0xFFFFFBFBFFFFC69219B0
```

BOOT set (`messungen/boot/*.sr`, short preset):

```text
BOOT1=0x0000000000607706DB00|0xFFFFFFFFFFFF11F249FF;BOOT2=0x0000040400603966864F|0xFFFFF7F7FFFF8D32F361;BOOT3=0x0000080800C072CD0C9F|0xFFFFFBFBFFFFC69979B0;BOOT4=0x0000000000C0EE0DB601|0xFFFFFFFFFFFF88F924FF
```

### Validation

Decoder works when annotation rows show frame entries (for example `F1`, `F2`)
and payload strings over stable regions.

## Auto Decode Wrapper (Profile Auto-Selection)

Use the wrapper to decode files directly without manually selecting anchor sets.
It auto-selects profile by path:

1. `boot` profile for files in `messungen/boot/`.
2. `alt` profile for `messungen/alt/pool_*.sr`.
3. `global` profile for everything else.

Preview selected profile and full command:

```bash
/Users/lukas/sundance/.venv/bin/python decoder/panel96_auto_decode.py \
	messungen/alt/pool_26-27.sr messungen/boot/boot1.sr --preview
```

Run real decode:

```bash
/Users/lukas/sundance/.venv/bin/python decoder/panel96_auto_decode.py \
	messungen/alt/pool_26-27.sr messungen/boot/boot1.sr
```

Default output uses semantic labels where known (for example
`TIME_12_00`, `TIME_8_00`, `TIME_12_45`, `TEMP_29_9C`).

Optional: force one profile for all inputs:

```bash
/Users/lukas/sundance/.venv/bin/python decoder/panel96_auto_decode.py \
	messungen/alt/pool_26-27.sr --profile alt
```

Optional: show raw state labels (`ST*`, `ALT*`, `BOOT*`) instead of semantic
value labels:

```bash
/Users/lukas/sundance/.venv/bin/python decoder/panel96_auto_decode.py \
	messungen/12-00_8-00.sr --label-mode state
```

### Current Coverage Status (After Extended ALT/BOOT Anchors)

Recent measured UNKNOWN rates with `panel96_auto_decode.py`:

1. `messungen/alt/pool_26-27.sr`: 0.4%
2. `messungen/alt/pool_27-28.sr`: 0.4%
3. `messungen/alt/pool_28-29.sr`: 0.4%
4. `messungen/alt/pool_29-30.sr`: 0.0%
5. `messungen/boot/boot1.sr`: 2.7%
6. `messungen/boot/boot2.sr`: 1.4%
7. `messungen/boot/boot3lang.sr`: 0.4%
8. `messungen/boot/boot4lang.sr`: 1.2%

`blind.sr` still has a significantly higher unknown share and should be handled
as a separate calibration target.

### Unknown Collector (Calibration Helper)

Use this helper to extract dominant remaining UNKNOWN signature pairs:

```bash
/Users/lukas/sundance/.venv/bin/python decoder/panel96_collect_unknowns.py \
	messungen --top 12
```

The output includes:

1. UNKNOWN summary per profile (`global`, `alt`, `boot`)
2. Top UNKNOWN pairs per profile
3. Ready-to-paste candidate anchors (`STX*`, `ALTX*`, `BOOTX*`)
