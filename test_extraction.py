#!/usr/bin/env python3
"""Test LangExtract extraction with verified API key."""

import os
import sys

# Check API key is set
if not os.getenv('LANGEXTRACT_API_KEY'):
    raise ValueError("LANGEXTRACT_API_KEY environment variable not set")

import langextract as lx
import textwrap

print("=" * 60)
print("Testing LangExtract with Gemini API")
print("=" * 60)

# Verify key is set
api_key = os.getenv('LANGEXTRACT_API_KEY')
print(f"✓ API Key set: {api_key[:20]}...{api_key[-10:]}\n")

prompt = textwrap.dedent("""\
    Extract characters and their emotions.
    Use exact text from the input.
    Do not paraphrase.""")

examples = [
    lx.data.ExampleData(
        text="Romeo gazed at Juliet with deep love.",
        extractions=[
            lx.data.Extraction(
                extraction_class="character",
                extraction_text="Romeo",
                attributes={"emotion": "love"}
            ),
        ]
    )
]

text = "Juliet felt sad watching the stars, longing for Romeo."

print(f"Input text:\n  '{text}'\n")
print("Running extraction with gemini-3.5-flash...\n")

try:
    result = lx.extract(
        text_or_documents=text,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-3.6-flash",
    )

    print("\n✓ SUCCESS!\n")
    print(f"Extracted {len(result.extractions)} items:\n")

    for i, extraction in enumerate(result.extractions, 1):
        print(f"{i}. {extraction.extraction_class.upper()}")
        print(f"   Text: '{extraction.extraction_text}'")
        if extraction.attributes:
            print(f"   Attributes: {extraction.attributes}")
        if extraction.char_interval:
            print(f"   Position: [{extraction.char_interval.start_pos}:{extraction.char_interval.end_pos}]")
        print()

    print("=" * 60)
    print("🎉 LangExtract is fully operational!")
    print("=" * 60)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
