#!/usr/bin/env python3
"""Test LangExtract with real sample text."""

import os
import sys

# Check API key is set
if not os.getenv('LANGEXTRACT_API_KEY'):
    raise ValueError("LANGEXTRACT_API_KEY environment variable not set")

import langextract as lx
import textwrap

# Sample text - Movie review
SAMPLE_TEXT = textwrap.dedent("""\
    Inception (2010) is a groundbreaking science fiction film directed by Christopher Nolan.
    The film stars Leonardo DiCaprio as Cobb, a skilled thief who specializes in extraction—stealing
    secrets from people's subconscious while they dream. Tom Hardy plays Eames, a forger, while
    Marion Cotillard plays Mal, Cobb's mysterious wife. The plot follows Cobb as he attempts
    one last job: instead of stealing an idea, he must plant one in someone's mind (inception).

    Released on July 16, 2010, Inception was a critical and commercial success, grossing
    over $839 million worldwide. The film received 8 Academy Award nominations, winning Oscars
    for Best Cinematography and Best Sound Mixing. Roger Ebert gave it 4 out of 4 stars,
    praising its originality and complexity. Critics noted that the film's nested dream sequences
    and philosophical themes set it apart from typical blockbusters.

    Nolan's use of practical effects and innovative camera work impressed audiences and filmmakers alike.
    The non-linear narrative structure, combined with Hans Zimmer's iconic score, created an immersive
    experience. The film's ending remains ambiguous—a spinning top suggests reality may be questioned—
    leaving viewers debating for years whether Cobb truly escaped the dream world.
    """)

print("=" * 70)
print("LangExtract Test - Sample Movie Review")
print("=" * 70)
print(f"\nSample Text ({len(SAMPLE_TEXT)} chars):\n")
print(SAMPLE_TEXT)
print("\n" + "=" * 70)

# Test 1: Extract People
print("\n[TEST 1] Extracting People and Their Roles\n")
print("-" * 70)

prompt_people = textwrap.dedent("""\
    Extract people mentioned in this film review and their roles.
    For each person, identify:
    - Their name (exact text from document)
    - Their role in the film (director, actor, composer, etc.)
    - What character they played (if applicable)

    Use exact text from the document. Do not paraphrase.""")

examples_people = [
    lx.data.ExampleData(
        text="Tom Hardy plays Eames, a forger, while Marion Cotillard plays Mal.",
        extractions=[
            lx.data.Extraction(
                extraction_class="person",
                extraction_text="Tom Hardy",
                attributes={"role": "actor", "character": "Eames"}
            ),
            lx.data.Extraction(
                extraction_class="person",
                extraction_text="Marion Cotillard",
                attributes={"role": "actor", "character": "Mal"}
            ),
        ]
    )
]

try:
    result_people = lx.extract(
        text_or_documents=SAMPLE_TEXT,
        prompt_description=prompt_people,
        examples=examples_people,
        model_id="gemini-3.6-flash",
    )

    print(f"✓ Found {len(result_people.extractions)} people:\n")
    for extraction in result_people.extractions:
        print(f"  • {extraction.extraction_text}")
        if extraction.attributes:
            for key, value in extraction.attributes.items():
                print(f"    - {key}: {value}")
        print()

except Exception as e:
    print(f"✗ Error: {e}\n")

# Test 2: Extract Key Facts
print("\n[TEST 2] Extracting Key Facts and Achievements\n")
print("-" * 70)

prompt_facts = textwrap.dedent("""\
    Extract important facts about the film mentioned in this review:
    - Release date
    - Box office numbers
    - Awards won
    - Critical scores/reviews

    Use exact text from the document.""")

examples_facts = [
    lx.data.ExampleData(
        text="Released on July 16, 2010, Inception was a critical and commercial success, grossing over $839 million worldwide.",
        extractions=[
            lx.data.Extraction(
                extraction_class="fact",
                extraction_text="Released on July 16, 2010",
                attributes={"type": "release_date"}
            ),
            lx.data.Extraction(
                extraction_class="fact",
                extraction_text="grossing over $839 million worldwide",
                attributes={"type": "box_office"}
            ),
        ]
    )
]

try:
    result_facts = lx.extract(
        text_or_documents=SAMPLE_TEXT,
        prompt_description=prompt_facts,
        examples=examples_facts,
        model_id="gemini-3.6-flash",
    )

    print(f"✓ Found {len(result_facts.extractions)} facts:\n")
    for extraction in result_facts.extractions:
        print(f"  • {extraction.extraction_text}")
        if extraction.attributes:
            print(f"    Type: {extraction.attributes.get('type', 'N/A')}")
        print()

except Exception as e:
    print(f"✗ Error: {e}\n")

# Test 3: Extract Themes and Elements
print("\n[TEST 3] Extracting Themes and Notable Elements\n")
print("-" * 70)

prompt_themes = textwrap.dedent("""\
    Extract important themes and notable elements mentioned in this review:
    - Narrative techniques used
    - Technical achievements
    - Themes or concepts

    Use exact text from the document.""")

examples_themes = [
    lx.data.ExampleData(
        text="The non-linear narrative structure, combined with Hans Zimmer's iconic score, created an immersive experience.",
        extractions=[
            lx.data.Extraction(
                extraction_class="element",
                extraction_text="non-linear narrative structure",
                attributes={"category": "narrative_technique"}
            ),
            lx.data.Extraction(
                extraction_class="element",
                extraction_text="Hans Zimmer's iconic score",
                attributes={"category": "technical_achievement"}
            ),
        ]
    )
]

try:
    result_themes = lx.extract(
        text_or_documents=SAMPLE_TEXT,
        prompt_description=prompt_themes,
        examples=examples_themes,
        model_id="gemini-3.6-flash",
    )

    print(f"✓ Found {len(result_themes.extractions)} elements:\n")
    for extraction in result_themes.extractions:
        print(f"  • {extraction.extraction_text}")
        if extraction.attributes:
            print(f"    Category: {extraction.attributes.get('category', 'N/A')}")
        print()

except Exception as e:
    print(f"✗ Error: {e}\n")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Test 1 - People: {len(result_people.extractions)} extracted")
print(f"Test 2 - Facts: {len(result_facts.extractions)} extracted")
print(f"Test 3 - Elements: {len(result_themes.extractions)} extracted")
print(f"\nTotal: {len(result_people.extractions) + len(result_facts.extractions) + len(result_themes.extractions)} items extracted")
print("\n✓ All tests completed successfully!")
print("=" * 70)
