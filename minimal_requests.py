#!/usr/bin/env python3
"""Minimal request extraction - 1 request per document."""

import os
if not os.getenv('LANGEXTRACT_API_KEY'):
    raise ValueError("LANGEXTRACT_API_KEY environment variable not set")

import langextract as lx

print("=" * 70)
print("MINIMAL REQUESTS EXTRACTION")
print("=" * 70)

# Small sample text (under default chunk size)
text = """
Inception (2010) is directed by Christopher Nolan. The film stars
Leonardo DiCaprio as Cobb, a skilled thief. Tom Hardy plays Eames,
a forger, while Marion Cotillard plays Mal, Cobb's wife.
"""

prompt = "Extract actors and characters they play."

examples = [
    lx.data.ExampleData(
        text="Leonardo DiCaprio as Cobb and Tom Hardy as Eames",
        extractions=[
            lx.data.Extraction(
                extraction_class="actor",
                extraction_text="Leonardo DiCaprio",
                attributes={"character": "Cobb"}
            ),
        ]
    )
]

print("\n🎯 OPTIMIZATION SETTINGS:\n")
print("✓ No chunking (text < 3000 chars)")
print("✓ 1 extraction pass (no multiple passes)")
print("✓ Sequential processing (no parallel requests)")
print("✓ No retries on small texts")
print("✓ Single API call expected\n")

print("Running extraction...")
print("-" * 70)

try:
    result = lx.extract(
        text_or_documents=text,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-3.6-flash",
        # Key parameters to minimize requests:
        extraction_passes=1,       # Only 1 pass (default anyway)
        max_workers=1,             # Sequential, not parallel (default=5)
        # No chunking if text is small
    )

    print(f"\n✓ SUCCESS with minimal requests!\n")
    print(f"Found {len(result.extractions)} actors:\n")

    for extraction in result.extractions:
        actor = extraction.extraction_text
        character = extraction.attributes.get('character', 'N/A') if extraction.attributes else 'N/A'
        print(f"  • {actor} → {character}")

except Exception as e:
    print(f"Error: {e}")
