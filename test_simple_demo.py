#!/usr/bin/env python3
"""Simple LangExtract demo - Extract actors and characters."""

import os
if not os.getenv('LANGEXTRACT_API_KEY'):
    raise ValueError("LANGEXTRACT_API_KEY environment variable not set")

import langextract as lx

# Sample text
text = """
Inception (2010) is directed by Christopher Nolan. The film stars Leonardo DiCaprio as Cobb,
a skilled thief. Tom Hardy plays Eames, a forger, while Marion Cotillard plays Mal, Cobb's wife.
Joseph Gordon-Levitt plays Arthur, Cobb's right-hand man.
"""

print("=" * 70)
print("LANGEXTRACT DEMO - Extract Actors and Characters")
print("=" * 70)
print(f"\nSample Text:\n{text}\n")

# Define extraction task
prompt = "Extract actors and the characters they play. List name and character."

examples = [
    lx.data.ExampleData(
        text="Leonardo DiCaprio as Cobb and Tom Hardy as Eames",
        extractions=[
            lx.data.Extraction(
                extraction_class="actor",
                extraction_text="Leonardo DiCaprio",
                attributes={"character": "Cobb"}
            ),
            lx.data.Extraction(
                extraction_class="actor",
                extraction_text="Tom Hardy",
                attributes={"character": "Eames"}
            ),
        ]
    )
]

print("Running extraction...")
print("-" * 70)

try:
    result = lx.extract(
        text_or_documents=text,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-3.6-flash",
    )

    print(f"\n✓ EXTRACTION COMPLETE!\n")
    print(f"Found {len(result.extractions)} actors:\n")

    for i, extraction in enumerate(result.extractions, 1):
        actor = extraction.extraction_text
        character = extraction.attributes.get('character', 'N/A') if extraction.attributes else 'N/A'
        print(f"  {i}. {actor} → {character}")
        if extraction.char_interval:
            print(f"     [Position: {extraction.char_interval.start_pos}:{extraction.char_interval.end_pos}]")

    print("\n" + "=" * 70)
    print("Demo completed successfully! 🎉")
    print("=" * 70)

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
