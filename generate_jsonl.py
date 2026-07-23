#!/usr/bin/env python3
"""Generate JSONL and visualization from extraction."""

import os
if not os.getenv('LANGEXTRACT_API_KEY'):
    raise ValueError("LANGEXTRACT_API_KEY environment variable not set")

import langextract as lx
import json

print("=" * 70)
print("Generating JSONL Output and Visualization")
print("=" * 70)

# Sample text
text = """
Inception (2010) is directed by Christopher Nolan. The film stars Leonardo DiCaprio as Cobb,
a skilled thief. Tom Hardy plays Eames, a forger, while Marion Cotillard plays Mal, Cobb's wife.
Joseph Gordon-Levitt plays Arthur, Cobb's right-hand man.
"""

prompt = "Extract actors and the characters they play."

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

print("\nRunning extraction...")
result = lx.extract(
    text_or_documents=text,
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-3.6-flash",
)

print(f"✓ Found {len(result.extractions)} actors\n")

# Save the results to a JSONL file
print("Saving to JSONL...")
lx.io.save_annotated_documents([result], output_name="extraction_results.jsonl", output_dir=".")

# Generate the visualization from the file
print("Generating visualization...")
html_content = lx.visualize("extraction_results.jsonl")
with open("visualization.html", "w") as f:
    if hasattr(html_content, 'data'):
        f.write(html_content.data)  # For Jupyter/Colab
    else:
        f.write(html_content)

print("\n" + "=" * 70)
print("FILES CREATED:")
print("=" * 70)
print("✓ extraction_results.jsonl (structured data)")
print("✓ visualization.html (interactive visualization)")
print("=" * 70)

# Display JSONL content
print("\nJSONL CONTENT:\n")
with open("extraction_results.jsonl", "r") as f:
    for i, line in enumerate(f, 1):
        data = json.loads(line)
        print(f"Record {i}:")
        print(json.dumps(data, indent=2))
