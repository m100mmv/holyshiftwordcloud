"""CLI entrypoint for generating the theological word cloud HTML file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Sequence

from wordcloud_core import (
    DEFAULT_PALETTE,
    DEFAULT_STOP_GROUPS,
    THEME_PRESETS,
    WordCloudConfig,
    generate_words_from_file,
    render_html,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the Holy Shift word cloud HTML page.")
    parser.add_argument(
        "input_path",
        nargs="?",
        default="data/holy-shift.ghost.2025-10-01-17-44-39.json",
        help="Path to the input JSON or text file.",
    )
    parser.add_argument(
        "html_path",
        nargs="?",
        default="output/holy_shift_wordcloud_portfolio_muted.html",
        help="Destination HTML file path.",
    )
    parser.add_argument("--max-items", type=int, default=420, help="Maximum number of tokens to render.")
    parser.add_argument("--min-font", type=int, default=9, help="Minimum font size in pixels.")
    parser.add_argument("--max-font", type=int, default=180, help="Maximum font size in pixels.")
    parser.add_argument("--curve-power", type=float, default=0.75, help="Exponent controlling the size curve aggressiveness.")
    parser.add_argument(
        "--disable-stop-group",
        action="append",
        choices=DEFAULT_STOP_GROUPS,
        default=[],
        help="Disable a built-in stopword group (can be specified multiple times).",
    )
    parser.add_argument(
        "--enable-stop-group",
        action="append",
        choices=DEFAULT_STOP_GROUPS,
        default=[],
        help="Ensure a stopword group is enabled (useful if you disabled all by default).",
    )
    parser.add_argument(
        "--extra-stop",
        action="append",
        default=[],
        help="Add a custom stopword (can be specified multiple times).",
    )
    parser.add_argument(
        "--remove-stop",
        action="append",
        default=[],
        help="Remove a word from the final stop list (can be specified multiple times).",
    )
    parser.add_argument(
        "--keep-short",
        action="append",
        default=[],
        help="Keep a short word (two letters or less) in the token list (can be specified multiple times).",
    )
    parser.add_argument(
        "--boost",
        action="append",
        default=[],
        metavar="PHRASE=FACTOR",
        help="Override or add a boost multiplier for a phrase (e.g. 'kingdom of god=3.5').",
    )
    parser.add_argument(
        "--json-key",
        action="append",
        default=[],
        metavar="KEY",
        help="JSON key whose values should be treated as text (repeatable).",
    )
    parser.add_argument(
        "--json-all-strings",
        action="store_true",
        help="Collect every string value in the JSON payload (ignores --json-key).",
    )
    parser.add_argument(
        "--input-type",
        choices=["auto", "json", "text"],
        default="auto",
        help="Force the input to be treated as JSON or plain text.",
    )
    parser.add_argument(
        "--no-references",
        action="store_true",
        help="Disable scripture/reference detection weighting.",
    )
    parser.add_argument(
        "--palette",
        type=str,
        default=None,
        help="Comma-delimited list of colour hex codes to override the default palette.",
    )
    parser.add_argument("--width", type=int, default=1920, help="Canvas width in pixels.")
    parser.add_argument("--height", type=int, default=1080, help="Canvas height in pixels.")
    parser.add_argument("--title", type=str, default="Holy Shift — Portfolio Word Cloud (Muted)", help="HTML document title.")
    parser.add_argument("--heading", type=str, default=None, help="Heading text displayed above the canvas.")
    parser.add_argument(
        "--font-family",
        type=str,
        default="Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial",
        help="Font stack used for rendering.",
    )
    parser.add_argument(
        "--dump-json",
        type=Path,
        default=None,
        help="Optional path to dump the processed word list as JSON alongside the HTML output.",
    )
    return parser.parse_args()


def parse_palette(raw: str | None) -> Sequence[str]:
    if not raw:
        return DEFAULT_PALETTE
    lower = raw.strip().lower()
    if lower in THEME_PRESETS:
        return THEME_PRESETS[lower]
    colours = [colour.strip() for colour in raw.split(",") if colour.strip()]
    return colours or DEFAULT_PALETTE


def parse_boosts(entries: Iterable[str]) -> dict[str, float]:
    overrides: dict[str, float] = {}
    for entry in entries:
        if "=" not in entry:
            continue
        phrase, value = entry.split("=", 1)
        phrase = phrase.strip().lower()
        try:
            overrides[phrase] = float(value)
        except ValueError:
            continue
    return overrides


def resolved_stop_groups(disabled: Iterable[str], enabled: Iterable[str]) -> set[str]:
    groups = set(DEFAULT_STOP_GROUPS)
    groups.difference_update(disabled)
    if enabled:
        groups.update(enabled)
    if not groups:
        groups.update(DEFAULT_STOP_GROUPS)
    return groups


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_path)
    html_path = Path(args.html_path)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    html_path.parent.mkdir(parents=True, exist_ok=True)

    config = WordCloudConfig(
        enabled_stop_groups=resolved_stop_groups(args.disable_stop_group, args.enable_stop_group),
        extra_stopwords=set(word.lower() for word in args.extra_stop),
        remove_stopwords=set(word.lower() for word in args.remove_stop),
        keep_short_extra=set(word.lower() for word in args.keep_short),
        max_items=args.max_items,
        max_font_size=args.max_font,
        min_font_size=args.min_font,
        size_curve_power=args.curve_power,
        collect_all_json_strings=args.json_all_strings,
        detect_references=not args.no_references,
    )

    if args.json_key:
        config.json_text_keys = {word.lower() for word in args.json_key}

    if args.boost:
        overrides = parse_boosts(args.boost)
        config.boost_map.update(overrides)

    file_type = args.input_type if args.input_type != "auto" else None
    words = generate_words_from_file(input_path, config=config, file_type=file_type)

    palette = parse_palette(args.palette)
    html = render_html(
        words,
        palette=palette,
        width=args.width,
        height=args.height,
        title=args.title,
        heading=args.heading,
        font_family=args.font_family,
    )

    html_path.write_text(html, encoding="utf-8")
    print(html_path)

    if args.dump_json:
        args.dump_json.parent.mkdir(parents=True, exist_ok=True)
        args.dump_json.write_text(json.dumps(words, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
