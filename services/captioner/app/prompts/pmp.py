"""Pragmatic Metacognitive Prompting (PMP) for the sarcastic style.

Sarcasm requires reasoning about the gap between literal content and intended
meaning. Rather than asking the model to "be sarcastic" directly, PMP walks it
through an explicit four-step chain before it writes the caption:

    (a) list the literal facts,
    (b) find the contradictions / incongruities,
    (c) derive the pragmatic (intended, non-literal) meaning,
    (d) write the dry, biting caption.

This helper produces the intermediate reasoning scaffold that is prepended to
the sarcastic system prompt.
"""

from __future__ import annotations

from app.core.schema import Style
from app.prompts.styles import get_style_prompt

PMP_INSTRUCTION = (
    "Before writing, reason silently through these steps, then output ONLY the final "
    "caption:\n"
    "1. LITERAL FACTS: Enumerate exactly what is seen and heard, without interpretation.\n"
    "2. CONTRADICTIONS: Identify incongruities — effort vs. outcome, intent vs. result, "
    "expectation vs. reality.\n"
    "3. PRAGMATIC MEANING: Infer what the scene really 'says' beyond its literal content.\n"
    "4. DRY CAPTION: Write one sharp, ironic, dismissive caption that lands the contradiction."
)


def build_pmp_messages(
    transcript_text: str,
    include_system: bool = True,
) -> list[dict[str, str]]:
    """Build the metacognitive chat messages for a sarcastic caption.

    The returned messages carry the sarcastic persona plus the PMP reasoning
    scaffold. Image content is inserted separately by the synthesizer, which
    orders the final prompt as: images -> transcript text -> style/system prompt.

    Args:
        transcript_text: The transcript to reason over.
        include_system: When ``True``, prepend the sarcastic system persona as a
            dedicated ``system`` message.

    Returns:
        A list of ``{"role": ..., "content": ...}`` chat messages.
    """
    messages: list[dict[str, str]] = []
    if include_system:
        messages.append({"role": "system", "content": get_style_prompt(Style.SARCASTIC)})

    user_content = (
        f"Transcript:\n{transcript_text.strip() or '(no speech detected)'}\n\n{PMP_INSTRUCTION}"
    )
    messages.append({"role": "user", "content": user_content})
    return messages
