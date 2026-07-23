#!/usr/bin/env python3
"""Basic LangExtract demo - shows library structure without needing API keys."""

import langextract as lx
from langextract.core import data

# Create some example data structures to show the API
print("=" * 60)
print("LangExtract Demo - Data Structure Examples")
print("=" * 60)

# 1. Create a CharInterval (character position in text)
char_interval = lx.core.data.CharInterval(start_pos=0, end_pos=6)
print(f"\n1. CharInterval: {char_interval}")

# 2. Create an Extraction
extraction = lx.core.data.Extraction(
    extraction_class="person",
    extraction_text="Romeo",
    char_interval=char_interval,
    attributes={"role": "protagonist"}
)
print(f"\n2. Extraction:")
print(f"   - Class: {extraction.extraction_class}")
print(f"   - Text: {extraction.extraction_text}")
print(f"   - Char interval: {extraction.char_interval}")
print(f"   - Attributes: {extraction.attributes}")

# 3. Create an ExampleData for few-shot learning
example = lx.data.ExampleData(
    text="Romeo and Juliet were in love.",
    extractions=[
        lx.data.Extraction(
            extraction_class="person",
            extraction_text="Romeo",
            attributes={"role": "protagonist"}
        ),
        lx.data.Extraction(
            extraction_class="person",
            extraction_text="Juliet",
            attributes={"role": "protagonist"}
        ),
    ]
)
print(f"\n3. ExampleData (few-shot example):")
print(f"   - Text: {example.text}")
print(f"   - Extractions: {len(example.extractions)} items")
for i, ext in enumerate(example.extractions, 1):
    print(f"     {i}. {ext.extraction_class}: '{ext.extraction_text}'")

# 4. Show available modules
print(f"\n4. Available LangExtract modules:")
public_api = [name for name in dir(lx) if not name.startswith('_')]
for name in public_api:
    print(f"   - {name}")

# 5. Show providers
print(f"\n5. Available LLM Providers:")
try:
    from langextract.providers import router
    print(f"   - Provider routing system loaded")
    print(f"   - Supports: Gemini, OpenAI, Ollama")
except Exception as e:
    print(f"   - Error: {e}")

print("\n" + "=" * 60)
print("✓ LangExtract is ready to use!")
print("=" * 60)
print("\nNext steps:")
print("1. Set up API key: export LANGEXTRACT_API_KEY='your-key'")
print("2. Run: lx.extract(text, prompt, examples, model_id='gemini-3.6-flash')")
print("3. Visualize: lx.visualize('results.jsonl')")
print("\nSee examples/ directory for full examples.")
