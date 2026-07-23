#!/usr/bin/env python3
"""Create visualization from extraction results."""

import os
if not os.getenv('LANGEXTRACT_API_KEY'):
    raise ValueError("LANGEXTRACT_API_KEY environment variable not set")

import langextract as lx

print("=" * 70)
print("Creating Visualization from Extraction")
print("=" * 70)

# Sample text
text = "Juliet felt sad watching the stars, longing for Romeo."

prompt = "Extract characters and their emotions."

examples = [
    lx.data.ExampleData(
        text="Romeo felt joyful watching Juliet dance.",
        extractions=[
            lx.data.Extraction(
                extraction_class="character",
                extraction_text="Romeo",
                attributes={"emotion": "joyful"}
            ),
        ]
    )
]

print(f"\nInput text:\n  '{text}'\n")
print("Step 1: Running extraction...")

result = lx.extract(
    text_or_documents=text,
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-3.6-flash",
    extraction_passes=1,
    max_workers=1,
)

print(f"✓ Found {len(result.extractions)} extractions\n")

# Step 2: Save to JSONL
print("Step 2: Saving to JSONL...")
lx.io.save_annotated_documents([result], output_name="extraction_results.jsonl", output_dir=".")
print("✓ Saved to extraction_results.jsonl\n")

# Step 3: Generate visualization
print("Step 3: Generating HTML visualization...")
html_content = lx.visualize("extraction_results.jsonl")

with open("visualization.html", "w") as f:
    if hasattr(html_content, 'data'):
        f.write(html_content.data)  # For Jupyter/Colab
    else:
        f.write(html_content)

print("✓ Saved to visualization.html\n")

print("=" * 70)
print("FILES CREATED:")
print("=" * 70)
print("✓ extraction_results.jsonl (structured data)")
print("✓ visualization.html (interactive visualization)")
print("\nOpen visualization.html in your browser to see the results!")
print("=" * 70)
