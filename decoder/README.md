# Decoder Prototype

Warning: this decoder is an experimental prototype and is not yet a complete, production-grade reverse-engineering tool.

## Purpose

This folder contains a trimmed-down, experimental Panel96-focused decoder for inspecting Sigrok `.sr` recordings from older Sundance Series 880 spa hardware. The goal is to keep the core workflow centered on the Panel96 frame model while retaining the mapping and template helpers that support it.

## Current status

- Prototype quality only
- Some decoding heuristics are still rough and may change as more captures are analyzed
- Annotation import and comparison are intended as a first step toward a richer capture workflow, not a finished parser
- The CLI output is useful for exploration, but should not be treated as authoritative device documentation

## Core Panel96 path

The practical core of the current prototype is:

- [decoder/panel96_protocol_decoder.py](panel96_protocol_decoder.py) — Panel96 frame-oriented decoding entry point
- [decoder/panel96_number_timeline.py](panel96_number_timeline.py) — timeline-style decoding and state tracking
- [decoder/frame96_mapper.py](frame96_mapper.py) — 96-bit frame extraction and mapping helpers
- [decoder/frame96_state_decoder.py](frame96_state_decoder.py) — state decoding based on mapped frame signatures
- [decoder/export_semantic_anchors.py](export_semantic_anchors.py) — export of semantic anchor candidates for calibration

The following helper modules still belong to the core workflow because the Panel96 path depends on them:

- [decoder/boot_align.py](boot_align.py) — shared capture alignment and bit-stream helpers
- [decoder/sr_reader.py](sr_reader.py) — `.sr` loading and low-level sample access

The rest of the decoder scripts are currently treated as optional experiments and are not required for the minimal Panel96 path.

## How to try it

From the repository root:

```bash
python3 decoder/decode_sr.py measurements/12-00_8-00.sr --annotation-json measurements/12-00_8-00.json
```

## Notes

- The decoder is intended for exploratory analysis and local experimentation.
- It is not affiliated with Sundance or Jacuzzi.
- It is meant to support non-profit, home-based analysis of older spa hardware where no modern interface exists.
- The Panel96 path remains a prototype and should not be treated as finished or authoritative device documentation.
