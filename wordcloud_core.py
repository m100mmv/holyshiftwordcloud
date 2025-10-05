"""Core utilities for generating theological word cloud data."""
from __future__ import annotations

import collections
import json
import re
from collections.abc import Mapping as MappingABC, Sequence as SequenceABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np

BOOK_NAMES: Sequence[str] = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
    "1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah",
    "Esther","Job","Psalm","Psalms","Proverbs","Ecclesiastes","Song of Songs","Isaiah","Jeremiah",
    "Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos","Obadiah","Jonah","Micah","Nahum",
    "Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew","Mark","Luke","John","Acts",
    "Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians","Colossians",
    "1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James",
    "1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation",
]

BOOK_PATTERN = r"(?:%s)" % "|".join([re.escape(b) for b in BOOK_NAMES])
REF_REGEX = re.compile(rf"\b{BOOK_PATTERN}\s+\d+(?::\d+(?:-\d+)?)?\b", re.IGNORECASE)

BASE_STOP = set("""a about above after again against all am an and any are as at be because been before being below
between both but by can did do does doing down during each few for from further had has have having he her here hers
herself him himself his how i if in into is it its itself just let me more most my myself no nor not of off on once only
or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then
there these they this those through to too under until up very was we were what when where which while who whom why will
with you your yours yourself yourselves""".split())

CONTRACTIONS = {
    "dont","doesnt","didnt","isnt","arent","wasnt","werent",
    "cant","couldnt","shouldnt","wouldnt","wont",
    "im","ive","youre","weve","theyre","its","thats",
    "ill","youll","theyll","were",
    "ve","re","ll","d","m","s",
}

FILLERS = {
    "really","quite","bit","lot","maybe","perhaps","sort","kind","thing","things","like","well","just","still","also",
    "yes","ok","okay","hmm","wow","oh","please","much","many","little","first","last","next","good","great","right",
}

PLATFORM = {
    "holy","shift","journal","post","posts","blog","entry","entries","subscribe","subscriber","member","members",
    "newsletter","comment","comments","signin","signup","signed","feature","featured","image","figure","caption",
    "thumb","bookmark","paywall","com","org","uk","http","https","www","amp","nbsp","email","online",
}

ADMINISH = {
    "meeting","panel","portfolio","form","forms","draft","version","page","pages","section","order","list","listening",
    "sent","received","phone","zoom","room","team","advisor","advisory","process","course","week","weeks","month","months",
    "year","years","today","tomorrow","yesterday","morning","evening","night","hour","hours","time","times","context",
}

PERSONAL = {"margie","thomas","andrew","frank","janice","shiftmatt","matt"}

SHORT_FILLERS = {
    "us","one","two","say","says","said","may","might","must","yet","got","get","go","goes","went","let","use",
    "look","new","old","away","back","keep","rather","already","probably","though","instead","ever","always",
}

KEEP_SHORT = {
    "god","jesus","hope","joy","love","amen","grace","sin","law","faith","word","rest",
    "paul","mark","john","luke","acts","job","ruth","jude","abba","yahweh",
}

BOOST_MAP = {
    "word and sacrament": 4.0, "pastoral care": 3.0, "kingdom of god": 3.0, "kingdom of heaven": 3.0,
    "covenant": 2.5, "grace": 2.0, "mercy": 2.0, "repentance": 2.5, "redemption": 2.5, "salvation": 2.5,
    "holiness": 2.5, "righteousness": 2.5, "discipleship": 2.2, "mission": 2.0, "ministry": 1.8, "vocation": 2.0,
    "calling": 2.0, "shepherd": 2.0, "pastor": 2.0, "flock": 2.0, "sacrament": 2.5, "sacraments": 2.5,
    "eucharist": 2.5, "communion": 2.5, "baptism": 2.5, "worship": 1.8, "prayer": 1.8, "psalm": 1.6, "scripture": 1.8,
    "bible": 1.8, "incarnation": 2.5, "resurrection": 2.5, "pentecost": 2.0, "advent": 2.0, "lent": 2.0, "epiphany": 2.0,
    "lord": 1.6, "saviour": 2.0, "savior": 2.0, "redeemer": 2.2, "alpha": 1.6, "omega": 1.6, "service": 1.2,
    "pastoral": 2.0, "sabbath": 2.0, "beatitudes": 2.0, "parable": 1.9, "parables": 1.9, "sanctification": 2.5,
}

THEME_PRESETS: Mapping[str, Sequence[str]] = {
    "muted": (
        "#0f172a","#334155","#475569","#64748b","#94a3b8","#cbd5e1",
        "#0b3d3a","#116a63","#2a8c82","#7fb3ad","#c9e3df",
        "#4a5b3f","#6b7f5a","#8fa37b","#b7c9a6",
        "#6b5e57","#8a7a70","#b3a79f",
        "#5b5b7a","#7a7aa0","#a3a3c4",
    ),
    "forest": (
        "#102418","#1f3f2b","#325c3b","#4a7d4d","#6a9f5f","#8fc172",
        "#b9db9c","#eff7d3",
    ),
    "sunrise": (
        "#1c1a4a","#3b3170","#6d3f9f","#a54bb7","#d855a8","#f26a7f",
        "#ffa86e","#fdd27f",
    ),
    "grayscale": (
        "#0f172a","#1f2937","#374151","#4b5563","#6b7280","#9ca3af",
        "#d1d5db","#e5e7eb","#f3f4f6",
    ),
    "ocean": (
        "#0b1f3a","#123c69","#1c5a8f","#2877b5","#3495db","#3fb3ff",
        "#72c9ff","#a6e0ff",
    ),
    "citrus": (
        "#231f20","#4a3424","#804a24","#ba5d21","#f97316","#fbbf24",
        "#fde047","#fef9c3",
    ),
}

DEFAULT_PALETTE: Sequence[str] = tuple(THEME_PRESETS["muted"])
DEFAULT_JSON_KEYS: Tuple[str, ...] = (
    "plaintext",
    "text",
    "body",
    "content",
    "excerpt",
    "summary",
    "description",
)

STOP_GROUPS: Mapping[str, Set[str]] = {
    "base": BASE_STOP,
    "contractions": CONTRACTIONS,
    "fillers": FILLERS,
    "platform": PLATFORM,
    "admin": ADMINISH,
    "personal": PERSONAL,
    "short": SHORT_FILLERS,
}

DEFAULT_STOP_GROUPS: Tuple[str, ...] = tuple(STOP_GROUPS.keys())

DEFAULT_WEIGHT_BREAKS: Tuple[Tuple[float, str], ...] = (
    (0.04, "900"),
    (0.12, "800"),
    (0.30, "700"),
    (0.60, "600"),
)


@dataclass
class WordCloudConfig:
    """Configuration for word cloud generation."""

    enabled_stop_groups: Set[str] = field(default_factory=lambda: set(DEFAULT_STOP_GROUPS))
    extra_stopwords: Set[str] = field(default_factory=set)
    remove_stopwords: Set[str] = field(default_factory=set)
    keep_short_extra: Set[str] = field(default_factory=set)
    max_items: int = 420
    max_font_size: int = 180
    min_font_size: int = 9
    size_curve_power: float = 0.75
    min_token_length: int = 3
    reference_weight: int = 4
    boost_map: Dict[str, float] = field(default_factory=lambda: dict(BOOST_MAP))
    weight_breaks: Tuple[Tuple[float, str], ...] = DEFAULT_WEIGHT_BREAKS
    detect_references: bool = True
    json_text_keys: Optional[Set[str]] = None
    collect_all_json_strings: bool = False
    manual_weight_adjustments: Dict[str, float] = field(default_factory=dict)

    def stopwords(self) -> Set[str]:
        stopwords: Set[str] = set()
        for name in self.enabled_stop_groups:
            stopwords.update(STOP_GROUPS.get(name, set()))
        stopwords.update(word.strip().lower() for word in self.extra_stopwords if word.strip())
        stopwords.difference_update(word.strip().lower() for word in self.remove_stopwords if word.strip())
        return stopwords

    def keep_short(self) -> Set[str]:
        keep: Set[str] = set(KEEP_SHORT)
        keep.update(word.strip().lower() for word in self.keep_short_extra if word.strip())
        return keep

    def resolved_json_keys(self) -> Set[str]:
        if self.collect_all_json_strings:
            return set()
        if self.json_text_keys:
            return {word.strip().lower() for word in self.json_text_keys if word.strip()}
        return {key.lower() for key in DEFAULT_JSON_KEYS}


@dataclass
class WordCountStat:
    key: str
    base_count: int
    reference_bonus: int
    bigram_count: int
    boost_multiplier: float
    manual_adjustment: float
    final_count: int


def norm_ref(match: str) -> str:
    parts = match.split()
    if not parts:
        return match
    book = " ".join([p.capitalize() if p.isalpha() else p for p in parts[:-1]])
    last = parts[-1] if len(parts) > 1 else ""
    return (book + " " + last).strip()


def split_weird_token(token: str) -> List[str]:
    adjusted = re.sub(r"([a-z])([A-Z])", r"\1 \2", token)
    adjusted = re.sub(r"([a-z])([0-9])", r"\1 \2", adjusted)
    adjusted = re.sub(r"([0-9])([a-z])", r"\1 \2", adjusted)
    return [piece for piece in adjusted.split() if piece]


def tokenize_text(body: str, *, stopwords: Set[str], keep_short: Set[str], min_length: int) -> List[str]:
    text = body.lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[_*`~^<>|\\]", " ", text)
    text = re.sub(r"\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"[^a-z0-9\s\'-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    raw_tokens: List[str] = []
    for token in text.split():
        raw_tokens.extend(split_weird_token(token))

    cleaned: List[str] = []
    for token in raw_tokens:
        token = token.strip("-'")
        if not token:
            continue
        if token in stopwords:
            continue
        if not re.fullmatch(r"[a-z]+'?[a-z]*", token):
            continue
        if len(token) < min_length and token not in keep_short:
            continue
        cleaned.append(token)
    return cleaned


def compute_word_weights(
    tokens: Sequence[str],
    references: Sequence[str],
    *,
    boost_map: Mapping[str, float],
    reference_weight: int,
    manual_adjustments: Optional[Mapping[str, float]] = None,
) -> tuple[Dict[str, int], Dict[str, WordCountStat]]:
    base_counts = collections.Counter(tokens)
    counts = base_counts.copy()

    reference_bonus = collections.Counter()
    for ref in references:
        counts[ref] += reference_weight
        reference_bonus[ref] += reference_weight

    bigrams = collections.Counter()
    for left, right in zip(tokens, tokens[1:]):
        phrase = f"{left} {right}"
        if phrase in boost_map:
            bigrams[phrase] += 1
            counts[phrase] = counts.get(phrase, 0) + 1

    manual_adjustments = manual_adjustments or {}
    final_counts: Dict[str, int] = dict(counts)
    stats: Dict[str, WordCountStat] = {}

    all_keys = set(final_counts.keys()) | {str(key) for key in manual_adjustments.keys()}

    for key in all_keys:
        base = base_counts.get(key, 0)
        ref_bonus = reference_bonus.get(key, 0)
        bigram_count = bigrams.get(key, 0)
        current = final_counts.get(key, 0)
        lowered = key.lower()
        boost_multiplier = float(boost_map.get(lowered, 1.0))
        if boost_multiplier != 1.0:
            current = int(round(current * boost_multiplier))

        manual_adjustment = float(
            manual_adjustments.get(key, manual_adjustments.get(lowered, 0.0))
        )
        if manual_adjustment:
            current = max(0, int(round(current + manual_adjustment)))

        final_counts[key] = current
        stats[key] = WordCountStat(
            key=key,
            base_count=base,
            reference_bonus=ref_bonus,
            bigram_count=bigram_count,
            boost_multiplier=boost_multiplier,
            manual_adjustment=manual_adjustment,
            final_count=current,
        )

    return final_counts, stats


def is_scripture_ref(value: str) -> bool:
    return bool(REF_REGEX.search(value))


def weight_for(rank: int, total: int, breaks: Sequence[Tuple[float, str]]) -> str:
    if total <= 1:
        return "600"
    fraction = rank / max(total - 1, 1)
    for threshold, weight in breaks:
        if fraction < threshold:
            return weight
    return "500"


def normalize_items(items: Mapping[str, int], *, max_items: int, min_font: int, max_font: int, curve_power: float, weight_breaks: Sequence[Tuple[float, str]]) -> List[Dict[str, object]]:
    filtered = {
        key: value
        for key, value in items.items()
        if is_scripture_ref(key) or re.fullmatch(r"[A-Za-z]+(?: [A-Za-z]+)*", key)
    }

    sorted_items = sorted(filtered.items(), key=lambda pair: pair[1], reverse=True)[:max_items]
    total = len(sorted_items)

    ranks = np.arange(total)
    curve = 1.0 - (ranks / max(total - 1, 1)) ** curve_power
    sizes = (min_font + (max_font - min_font) * curve).astype(int)

    data = []
    for idx, (word, _) in enumerate(sorted_items):
        data.append({
            "text": word,
            "size": int(sizes[idx]),
            "weight": weight_for(idx, total, weight_breaks),
        })
    return data


def load_plaintext(posts: Iterable[Mapping[str, object]]) -> str:
    return " ".join(str(post.get("plaintext", "")) for post in posts)


def extract_posts(payload: Mapping[str, object]) -> Sequence[Mapping[str, object]]:
    return payload.get("db", [{}])[0].get("data", {}).get("posts", [])  # type: ignore[return-value]


def extract_tokens_and_references(
    text: str, *, config: WordCloudConfig
) -> tuple[List[str], List[str]]:
    if config.detect_references:
        references = [norm_ref(match.group(0)) for match in REF_REGEX.finditer(text)]
    else:
        references = []
    tokens = tokenize_text(
        text,
        stopwords=config.stopwords(),
        keep_short=config.keep_short(),
        min_length=config.min_token_length,
    )
    return tokens, references


def prepare_word_data(
    text: str,
    *,
    config: WordCloudConfig,
    tokens: Optional[Sequence[str]] = None,
    references: Optional[Sequence[str]] = None,
) -> tuple[
    Dict[str, int],
    Dict[str, WordCountStat],
    List[str],
    List[str],
]:
    if tokens is None or references is None:
        tokens, references = extract_tokens_and_references(text, config=config)
    weights, stats = compute_word_weights(
        list(tokens),
        list(references),
        boost_map=config.boost_map,
        reference_weight=config.reference_weight,
        manual_adjustments=config.manual_weight_adjustments,
    )
    return weights, stats, list(tokens), list(references)


def generate_words_from_text(text: str, *, config: WordCloudConfig) -> List[Dict[str, object]]:
    weights, _, _, _ = prepare_word_data(text, config=config)
    return normalize_items(
        weights,
        max_items=config.max_items,
        min_font=config.min_font_size,
        max_font=config.max_font_size,
        curve_power=config.size_curve_power,
        weight_breaks=config.weight_breaks,
    )


def generate_words_and_stats_from_text(text: str, *, config: WordCloudConfig) -> tuple[
    List[Dict[str, object]],
    Dict[str, WordCountStat],
    Dict[str, int],
    List[str],
]:
    weights, stats, tokens, references = prepare_word_data(text, config=config)
    words = normalize_items(
        weights,
        max_items=config.max_items,
        min_font=config.min_font_size,
        max_font=config.max_font_size,
        curve_power=config.size_curve_power,
        weight_breaks=config.weight_breaks,
    )
    return words, stats, weights, references


def generate_words_and_stats_from_tokens(
    tokens: Sequence[str],
    references: Sequence[str],
    *,
    config: WordCloudConfig,
) -> tuple[List[Dict[str, object]], Dict[str, WordCountStat], Dict[str, int], List[str]]:
    weights, stats = compute_word_weights(
        list(tokens),
        list(references),
        boost_map=config.boost_map,
        reference_weight=config.reference_weight,
        manual_adjustments=config.manual_weight_adjustments,
    )
    words = normalize_items(
        weights,
        max_items=config.max_items,
        min_font=config.min_font_size,
        max_font=config.max_font_size,
        curve_power=config.size_curve_power,
        weight_breaks=config.weight_breaks,
    )
    return words, stats, weights, list(references)


def _iter_json_strings(value: object, *, keys: Set[str], collect_all: bool, include: bool = False) -> Iterable[str]:
    if isinstance(value, str):
        if collect_all or include or not keys:
            yield value
        return

    if isinstance(value, MappingABC):
        for raw_key, child in value.items():
            key_lower = str(raw_key).lower()
            child_include = collect_all or key_lower in keys or include
            yield from _iter_json_strings(child, keys=keys, collect_all=collect_all, include=child_include)
        return

    if isinstance(value, SequenceABC) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _iter_json_strings(child, keys=keys, collect_all=collect_all, include=include)


def extract_text_from_json_payload(payload: Mapping[str, object], *, config: WordCloudConfig) -> str:
    keys = config.resolved_json_keys()
    strings = list(_iter_json_strings(payload, keys=keys, collect_all=config.collect_all_json_strings))
    if not strings and not config.collect_all_json_strings and "plaintext" not in keys:
        # Fallback to historic Ghost behaviour if nothing matched.
        strings = [post.get(
            "plaintext", ""
        ) for post in extract_posts(payload)] if isinstance(payload, MappingABC) else []
    return " \n".join(s for s in strings if s)


def generate_words_from_posts(posts: Iterable[Mapping[str, object]], *, config: WordCloudConfig) -> List[Dict[str, object]]:
    text = load_plaintext(posts)
    return generate_words_from_text(text, config=config)


def generate_words_and_stats_from_posts(
    posts: Iterable[Mapping[str, object]], *, config: WordCloudConfig
) -> tuple[List[Dict[str, object]], Dict[str, WordCountStat], Dict[str, int], List[str]]:
    text = load_plaintext(posts)
    return generate_words_and_stats_from_text(text, config=config)


def generate_words_from_json_path(json_path: Path | str, *, config: WordCloudConfig) -> List[Dict[str, object]]:
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as infile:
        payload = json.load(infile)
    text = extract_text_from_json_payload(payload, config=config)
    return generate_words_from_text(text, config=config)


def generate_words_and_stats_from_json_path(
    json_path: Path | str, *, config: WordCloudConfig
) -> tuple[List[Dict[str, object]], Dict[str, WordCountStat], Dict[str, int], List[str]]:
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as infile:
        payload = json.load(infile)
    text = extract_text_from_json_payload(payload, config=config)
    return generate_words_and_stats_from_text(text, config=config)


def load_text_from_json_path(json_path: Path | str, *, config: WordCloudConfig) -> str:
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as infile:
        payload = json.load(infile)
    return extract_text_from_json_payload(payload, config=config)


def generate_words_from_text_path(text_path: Path | str, *, config: WordCloudConfig) -> List[Dict[str, object]]:
    path = Path(text_path)
    text = path.read_text(encoding="utf-8")
    return generate_words_from_text(text, config=config)


def generate_words_and_stats_from_text_path(
    text_path: Path | str, *, config: WordCloudConfig
) -> tuple[List[Dict[str, object]], Dict[str, WordCountStat], Dict[str, int], List[str]]:
    path = Path(text_path)
    text = path.read_text(encoding="utf-8")
    return generate_words_and_stats_from_text(text, config=config)


def load_text_from_text_path(text_path: Path | str) -> str:
    path = Path(text_path)
    return path.read_text(encoding="utf-8")


def generate_words_from_file(
    path: Path | str,
    *,
    config: WordCloudConfig,
    file_type: Optional[str] = None,
    prepared: Optional[Mapping[str, object]] = None,
) -> List[Dict[str, object]]:
    words, _, _, _ = generate_words_and_stats_from_file(
        path, config=config, file_type=file_type, prepared=prepared
    )
    return words


def generate_words_and_stats_from_file(
    path: Path | str,
    *,
    config: WordCloudConfig,
    file_type: Optional[str] = None,
    prepared: Optional[Mapping[str, object]] = None,
) -> tuple[List[Dict[str, object]], Dict[str, WordCountStat], Dict[str, int], List[str]]:
    target = Path(path)
    kind = (file_type or "auto").lower()

    if kind not in {"auto", "json", "text"}:
        kind = "auto"

    if kind == "auto":
        if target.suffix.lower() == ".json":
            kind = "json"
        else:
            kind = "text"

    if prepared:
        tokens = prepared.get("tokens")
        references = prepared.get("references")
    else:
        tokens = references = None

    if tokens is not None and references is not None:
        return generate_words_and_stats_from_tokens(tokens, references, config=config)

    if kind == "json":
        text = load_text_from_json_path(target, config=config)
    else:
        text = load_text_from_text_path(target)

    if prepared is not None and isinstance(prepared, dict):
        tokens, references = extract_tokens_and_references(text, config=config)
        prepared["tokens"] = list(tokens)
        prepared["references"] = list(references)
        return generate_words_and_stats_from_tokens(tokens, references, config=config)

    return generate_words_and_stats_from_text(text, config=config)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\"/>
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
<title>{title}</title>
<style>
  :root {{ --bg:#ffffff; --border:#e6e6ea; --text:#111827; }}
  html, body {{ height:100%; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family: ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", Roboto, Helvetica, Arial; }}
  header {{ padding:12px 16px; font-weight:700; letter-spacing:.2px; }}
  #wrap {{ display:flex; flex-direction:column; align-items:center; gap:10px; padding:10px; }}
  canvas {{ border:1px solid var(--border); width:100%; height:auto; max-width:{max_width}px; }}
  .controls {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
  button {{ padding:8px 12px; border-radius:10px; border:1px solid var(--border); background:#f8fafc; cursor:pointer; font-weight:600; }}
  button:hover {{ background:#eef2f7; }}
  .legend {{ font-size:12px; opacity:.75; }}
</style>
</head>
<body>
  <div id=\"wrap\">
    <header>{heading}</header>
    <div class=\"controls\">
      <button id=\"download\">Download PNG</button>
      <span id=\"status\" class=\"legend\">Laying out…</span>
    </div>
    <canvas id=\"cloud\" width=\"{width}\" height=\"{height}\"></canvas>
  </div>

  <script src=\"https://unpkg.com/d3@7\"></script>
  <script src=\"https://unpkg.com/d3-cloud/build/d3.layout.cloud.js\"></script>
  <script>
    const words = {words_js};
    const palette = {palette_js};
    const canvas = document.getElementById('cloud');
    const ctx = canvas.getContext('2d');
    const status = document.getElementById('status');
    const fontFamily = {font_family_js};

    function draw(placed) {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";
      placed.forEach((d, i) => {{
        ctx.save();
        ctx.translate(d.x + canvas.width / 2, d.y + canvas.height / 2);
        ctx.rotate(d.rotate * Math.PI / 180);
        ctx.font = `${{d.weight}} ${{d.size}}px ${{fontFamily}}`;
        ctx.fillStyle = palette[i % palette.length];
        ctx.fillText(d.text, 0, 0);
        ctx.restore();
      }});
      status.textContent = "Rendered • " + placed.length + " items";
    }}

    const layout = d3.layout.cloud()
      .size([canvas.width, canvas.height])
      .words(words.map(d => ({{...d}})))
      .padding(2)
      .rotate(() => (Math.random() < 0.96 ? 0 : (Math.random() < 0.5 ? -30 : 30)))
      .font(fontFamily)
      .fontWeight(d => d.weight)
      .fontSize(d => d.size)
      .on("end", draw);

    layout.start();

    document.getElementById('download').addEventListener('click', () => {{
      const url = canvas.toDataURL("image/png");
      const a = document.createElement('a');
      a.href = url;
      a.download = 'holy_shift_wordcloud_portfolio_muted.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }});
  </script>
</body>
</html>
"""


def render_html(words: Sequence[Mapping[str, object]], *, palette: Sequence[str] = DEFAULT_PALETTE, width: int = 1920, height: int = 1080, title: str = "Holy Shift — Portfolio Word Cloud (Muted)", heading: str | None = None, font_family: str = "Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial") -> str:
    heading_text = heading or "Holy Shift — Theological Word Cloud (Muted Palette)"
    return HTML_TEMPLATE.format(
        words_js=json.dumps(words),
        palette_js=json.dumps(list(palette)),
        width=width,
        height=height,
        max_width=width,
        title=title,
        heading=heading_text,
        font_family_js=json.dumps(font_family),
    )
