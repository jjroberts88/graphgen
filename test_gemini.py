#!/usr/bin/env python3
"""Test Gemini API with configured key."""

import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv('/Users/jamesroberts/Downloads/GraphGen/graphgen/.env')

api_key = os.getenv('LANGEXTRACT_API_KEY')

if not api_key:
    print("❌ No API key found!")
    print("   Make sure .env file exists with LANGEXTRACT_API_KEY set")
    sys.exit(1)

print("✓ API key loaded from .env")
print(f"  Key preview: {api_key[:20]}...{api_key[-10:]}")
print(f"  Key length: {len(api_key)} chars\n")

import langextract as lx
import textwrap

print("Initializing extraction task...\n")

prompt = textwrap.dedent("""\
    Extract characters and their emotions.
    Use exact text from input.""")

examples = [
    lx.data.ExampleData(
        text="Romeo loved Juliet deeply.",
        extractions=[
            lx.data.Extraction(
                extraction_class="person",
                extraction_text="Romeo",
                attributes={"emotion": "love"}
            ),
        ]
    )
]

input_text = "Juliet gazed sadly at the stars, longing for Romeo."

try:
    print("Starting extraction with gemini-3.5-flash...")
    print("(This may take a moment on first run)\n")

    result = lx.extract(
        text_or_documents=input_text,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-3.6-flash",
    )

    print("\n" + "="*60)
    print("✓ EXTRACTION SUCCESSFUL!")
    print("="*60)
    print(f"\nExtracted {len(result.extractions)} items from input:\n")
    print(f"Input: \"{input_text}\"\n")

    for i, extraction in enumerate(result.extractions, 1):
        print(f"{i}. {extraction.extraction_class.upper()}")
        print(f"   Text: '{extraction.extraction_text}'")
        if extraction.attributes:
            print(f"   Attributes: {extraction.attributes}")
        if extraction.char_interval:
            start = extraction.char_interval.start_pos
            end = extraction.char_interval.end_pos
            print(f"   Position: [{start}:{end}]")
        print()

    # Save results
    output_file = "extraction_result.jsonl"
    lx.io.save_annotated_documents([result], output_name=output_file, output_dir=".")
    print(f"✓ Results saved to {output_file}")

    # Generate visualization
    print("\nGenerating visualization...")
    html = lx.visualize(output_file)
    with open("extraction_visualization.html", "w") as f:
        if hasattr(html, 'data'):
            f.write(html.data)
        else:
            f.write(html)
    print("✓ Visualization saved to extraction_visualization.html")
    print("\nOpen extraction_visualization.html in your browser to see results!")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"   {str(e)[:200]}")
    print("\nTroubleshooting:")
    print("  • Verify API key is valid at https://aistudio.google.com/app/apikey")
    print("  • Check internet connection")
    print("  • Try again in a moment (API rate limits)")
    sys.exit(1)
