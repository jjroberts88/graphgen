# LangExtract Setup & Usage Guide

## ✓ Installation Complete

You now have LangExtract v1.6.0 fully installed and ready to use.

```bash
cd /Users/jamesroberts/Downloads/GraphGen/graphgen
```

## Quick Start

### 1. Set Up Your API Key

Choose one LLM provider:

**Option A: Google Gemini (Recommended)**
```bash
export LANGEXTRACT_API_KEY="your-gemini-api-key"
# Get key at: https://aistudio.google.com/app/apikey
```

**Option B: OpenAI**
```bash
export OPENAI_API_KEY="your-openai-key"
# Get key at: https://platform.openai.com/api-keys
```

**Option C: Local Ollama (No API Key)**
```bash
# Install Ollama from ollama.com
ollama pull gemma2:2b
ollama serve  # In separate terminal
```

### 2. Write Your First Extraction

Create `my_extraction.py`:

```python
import langextract as lx
import textwrap

# Define what to extract
prompt = textwrap.dedent("""\
    Extract characters and their emotions.
    Use exact text from the input. Do not paraphrase.
    """)

# Provide examples to guide the model
examples = [
    lx.data.ExampleData(
        text="Romeo gazed longingly at the stars.",
        extractions=[
            lx.data.Extraction(
                extraction_class="character",
                extraction_text="Romeo",
                attributes={"emotion": "longing"}
            ),
        ]
    )
]

# Run extraction
text = "Lady Juliet looked sadly out the window."
result = lx.extract(
    text_or_documents=text,
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-3.6-flash",  # or "gpt-4o", "gemma2:2b"
)

# Print results
for extraction in result.extractions:
    print(f"Found: {extraction.extraction_text}")
    print(f"  Class: {extraction.extraction_class}")
    print(f"  Attributes: {extraction.attributes}")
```

Run it:
```bash
python my_extraction.py
```

### 3. Visualize Results

```python
# Save results
lx.io.save_annotated_documents([result], output_name="results.jsonl")

# Generate interactive HTML
html = lx.visualize("results.jsonl")
with open("visualization.html", "w") as f:
    f.write(html)

# Open visualization.html in your browser
```

## Available Commands

### Run Tests
```bash
# All tests (skips those requiring API keys)
pytest tests -k "not live_api"

# Specific test
pytest tests/data_lib_test.py -v

# With coverage
pytest tests --cov=langextract
```

### Code Formatting
```bash
./autoformat.sh  # Format code
pylint --rcfile=.pylintrc langextract  # Lint
```

### Explore Examples
```bash
# Notebooks
ls examples/notebooks/

# Ollama examples
ls examples/ollama/

# Custom provider plugins
ls examples/custom_provider_plugin/
```

## Supported Models

### Gemini (Recommended)
- `gemini-3.6-flash` (fast, good quality)
- `gemini-3.1-flash-lite` (ultra-fast, cost-effective)
- `gemini-3.1-pro` (best quality)

### OpenAI
- `gpt-4o` (best quality)
- `gpt-4o-mini` (fast, cost-effective)
- `gpt-4` (good quality, slower)

### Ollama (Local)
- `gemma2:2b` (fast, small)
- `llama2:7b` (larger model)
- Any model you pull with `ollama pull <model>`

## Common Tasks

### Extract from URL
```python
result = lx.extract(
    text_or_documents="https://www.gutenberg.org/files/1513/1513-0.txt",
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-3.6-flash",
    extraction_passes=3,    # Multiple passes for better recall
    max_workers=20,         # Parallel processing
    max_char_buffer=1000    # Smaller chunks for accuracy
)
```

### Batch Processing with Vertex AI
```python
result = lx.extract(
    text_or_documents=documents,
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-3.6-flash",
    language_model_params={
        "vertexai": True,
        "project": "your-project-id",
        "location": "global",
        "batch": {
            "enabled": True,
            "threshold": 50,  # Use batch if > 50 docs
        }
    }
)
```

### Filter Grounded Extractions
```python
# Remove extractions not found in source text
grounded = [e for e in result.extractions if e.char_interval]
```

## Troubleshooting

### API Key Not Found
```bash
# Check it's set
echo $LANGEXTRACT_API_KEY

# Or use .env file
cat > .env << EOF
LANGEXTRACT_API_KEY=your-key-here
EOF
```

### Import Errors
```bash
# Verify installation
python -c "import langextract; print(langextract.__file__)"

# Reinstall if needed
pip install -e ".[test]"
```

### Test Failures
```bash
# Run verbose output
pytest tests/some_test.py -vv

# See what fails
pytest tests -x  # Stop on first failure
```

## Directory Structure

```
graphgen/
├── langextract/          # Main package
├── tests/                # Unit tests
├── examples/             # Example scripts & notebooks
│   ├── notebooks/        # Jupyter notebooks
│   ├── ollama/          # Ollama examples
│   └── custom_provider_plugin/  # Plugin template
├── docs/                # Documentation
├── CONTRIBUTING.md      # Development guide
└── README.md           # Full documentation
```

## Next Steps

1. **Read the README**: `cd graphgen && cat README.md`
2. **Explore Examples**: `ls examples/`
3. **Run Notebooks**: `jupyter notebook examples/notebooks/`
4. **Check Tests**: `pytest tests -v`
5. **Build Custom Extraction**: Use `my_extraction.py` template above

## Resources

- **GitHub**: https://github.com/google/langextract
- **API Docs**: Generated in `/docs` after running tests
- **Issues**: Report problems on GitHub
- **Contributing**: See `CONTRIBUTING.md` for development guide

## You're All Set! 🚀

```bash
cd /Users/jamesroberts/Downloads/GraphGen/graphgen
python ../demo_basic.py
python ../my_extraction.py  # After setting API key
```
