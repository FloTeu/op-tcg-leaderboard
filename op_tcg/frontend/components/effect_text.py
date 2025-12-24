from __future__ import annotations

from typing import List

from fasthtml import ft
from op_tcg.backend.models.cards import OPTcgAbility


def _get_tag_classes(tag_text: str) -> str:
    """Return tailwind classes for a bracket tag based on its semantics.

    Rules (case-insensitive):
    - Contains "don" -> black pill
    - Contains "once per turn" -> pink pill
    - Equals "trigger" -> yellow pill
    - Equals one of OPTcgAbility values (e.g., Rush, Blocker, Banish) -> orange pill
    - Otherwise -> blue pill
    """
    lower = tag_text.lower()
    base = "text-[10px] md:text-xs font-semibold px-2 py-0.5 rounded-full whitespace-nowrap"
    if "don" in lower:
        return f"{base} bg-black text-white"
    if any(effect in lower for effect in ["once per turn"]):
        return f"{base} bg-pink-600 text-white"
    if any(effect in lower for effect in ["counter"]):
        return f"{base} bg-red-600 text-white"
    if lower.strip() == "trigger":
        return f"{base} bg-yellow-300 text-black"
    # ability keywords from OPTcgAbility (excluding Trigger which is handled above)
    ability_values = {a.value.lower() for a in OPTcgAbility}
    if lower.strip() in ability_values:
        return f"{base} bg-yellow-600 text-white"
    return f"{base} bg-blue-600 text-white"


def _starts_new_sentence(text: str, index: int) -> bool:
    """Heuristically determine whether a tag at index starts a new sentence.

    Consider it sentence-starting when the previous non-space character is one of
    . ! ? ) or a newline. Index 0 is treated as not requiring a linebreak.
    """
    if index <= 0:
        return False
    j = index - 1
    while j >= 0 and text[j].isspace():
        if text[j] == "\n":
            return True
        j -= 1
    if j < 0:
        return False
    return text[j] in ".!?)"


def render_effect_text(effect_text: str | None, subject_name: str | None = None) -> ft.Div:
    """Render card effect text with styled bracketed segments.

    The function scans for bracketed segments like "[DON!!x3]" or
    "[Once Per Turn]" and wraps them in colored label pills. Everything else
    remains as normal text. This component is generic and can be reused on the
    leader page, card modal, or anywhere effect text appears.
    """
    if not effect_text:
        return ft.Div(ft.P("No effect text available.", cls="text-gray-400 text-sm"))

    import re

    parts: List = []
    last_end = 0

    for match in re.finditer(r"\[(.+?)\]", effect_text):
        start, end = match.span()
        # Append preceding plain text if any
        if start > last_end:
            parts.append(ft.Span(effect_text[last_end:start], cls="text-gray-200 text-sm"))
        tag_text = match.group(1)
        # Get two words before tag_text
        preceding_words = effect_text[:start].strip().split()[-2:]
        preceding_words_str = " ".join(preceding_words)

        # Insert a linebreak before sentence-starting bracket words
        if _starts_new_sentence(effect_text, start):
            parts.append(ft.Br())

        # Subject name inside brackets or other than -> no special styling
        if subject_name and tag_text.strip().lower() == subject_name.strip().lower():
            parts.append(ft.Span(f"[{tag_text}]", cls="text-gray-200 text-sm"))
        elif preceding_words_str.strip().lower() == "other than":
            parts.append(ft.Span(f"[{tag_text}]", cls="text-gray-200 text-sm"))
        else:
            parts.append(ft.Span(tag_text, cls=_get_tag_classes(tag_text)))
        # Add a small space after a tag for readability
        parts.append(ft.Span(" "))
        last_end = end

    # Append the remaining text after the last tag
    if last_end < len(effect_text):
        parts.append(ft.Span(effect_text[last_end:], cls="text-gray-200 text-sm"))

    return ft.Div(*parts)


