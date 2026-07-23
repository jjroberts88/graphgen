# Gemini API Request Optimization Guide

## Free Tier Limits

```
RPM (Requests Per Minute):  20
QPD (Queries Per Day):      300
Requests: ~6-7 per minute max
```

## How Many Requests Does Each Operation Make?

### Scenario 1: Small Text (< 3000 chars), No Params
```python
result = lx.extract(
    text_or_documents="Short text...",
    prompt_description="Extract...",
    examples=[...],
    model_id="gemini-3.6-flash",
)
```
**Requests: 1** ✓

### Scenario 2: Large Text (10,000+ chars), Default Params
```python
result = lx.extract(
    text_or_documents="Very long text...",  # > 3000 chars
    prompt_description="Extract...",
    examples=[...],
    model_id="gemini-3.6-flash",
)
```
**Requests: Multiple** (text is chunked)
- 10,000 chars ÷ 3000 = ~4 chunks = ~4 requests

### Scenario 3: Multiple Extraction Passes
```python
result = lx.extract(
    text_or_documents="text...",
    prompt_description="Extract...",
    examples=[...],
    model_id="gemini-3.6-flash",
    extraction_passes=3,  # <-- Multiple passes!
)
```
**Requests: 3x** (default)
- Small text: 1 chunk × 3 passes = 3 requests
- Large text: 4 chunks × 3 passes = 12 requests

### Scenario 4: Parallel Processing
```python
result = lx.extract(
    text_or_documents="text...",
    prompt_description="Extract...",
    examples=[...],
    model_id="gemini-3.6-flash",
    max_workers=5,  # <-- Parallel!
)
```
**Requests: Same as scenario, but sent in parallel**
- Can hit rate limits faster (all 5 requests at once)

## ✅ OPTIMIZATION: Minimize to 1 Request Per Document

### Code Template
```python
import langextract as lx

result = lx.extract(
    text_or_documents=text,          # Single text or list
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-3.6-flash",
    
    # Minimize requests:
    extraction_passes=1,             # Only 1 pass (find once)
    max_workers=1,                   # Sequential (not parallel)
    max_char_buffer=10000,           # Larger chunks (default 3000)
    # Result: ~1 request per 10K chars of text
)
```

### Request Count Table

| Text Size | extraction_passes | max_workers | Requests |
|-----------|-------------------|-------------|----------|
| < 3KB | 1 | 1 | **1** |
| < 10KB | 1 | 1 | **1** |
| 10-20KB | 1 | 1 | 2 |
| 20-30KB | 1 | 1 | 3 |
| Any | 3 | 1 | 3x (chunks) |
| Any | 1 | 5 | Same (parallel) |

## 🎯 Best Practices for Free Tier

### For Individual Extractions
```python
# ✓ GOOD - 1 request
result = lx.extract(
    text_or_documents=short_text,
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-3.6-flash",
    extraction_passes=1,      # Single pass
    max_workers=1,            # Sequential
)
```

### For Batch Processing
```python
# ✓ GOOD - Minimize parallel requests
results = []
docs = [doc1, doc2, doc3, ...]

for doc in docs:  # Process one at a time
    result = lx.extract(
        text_or_documents=doc,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-3.6-flash",
        extraction_passes=1,
        max_workers=1,
    )
    results.append(result)
    # ~1 request per document
    # Total: ~N requests for N documents
```

### For High-Quality Extraction (if you have quota)
```python
# ✓ GOOD - Use when you have quota
result = lx.extract(
    text_or_documents=text,
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-3.6-flash",
    extraction_passes=3,      # Multiple passes improve recall
    max_workers=5,            # Parallel speeds it up
    # Trade: More requests, better results
)
```

## 📊 Example: Processing 20 Documents

### Scenario A: Minimal Requests (Good for Free Tier)
```python
for doc in documents:  # 20 documents
    result = lx.extract(
        text_or_documents=doc,
        ...,
        extraction_passes=1,
        max_workers=1,
    )
# Total: ~20 requests (within free tier limit of 300/day)
```

### Scenario B: High Quality (Need Paid Tier)
```python
for doc in documents:  # 20 documents
    result = lx.extract(
        text_or_documents=doc,
        ...,
        extraction_passes=3,
        max_workers=5,
    )
# Total: ~60 requests (3x more)
# RPM: Could hit rate limit (5 parallel requests × 20 docs)
```

## 🚀 Parameters Explained

### `extraction_passes`
- **What it does**: Runs extraction multiple times to improve recall
- **Default**: 1
- **Effect on requests**: Multiplies request count by N
- **Optimization**: Keep at 1 for free tier

### `max_workers`
- **What it does**: Number of parallel API requests
- **Default**: 5
- **Effect on requests**: Same total, but sent faster (can hit RPM limit)
- **Optimization**: Set to 1 to spread requests over time

### `max_char_buffer`
- **What it does**: Maximum characters per chunk
- **Default**: 3000
- **Effect on requests**: Larger buffer = fewer chunks = fewer requests
- **Optimization**: Increase to 10000 to reduce chunking

### `text_or_documents`
- **What it does**: Single text (string) or multiple (list/generator)
- **Default**: Single string
- **Effect on requests**: List processes multiple (can batch efficiently)
- **Optimization**: Process lists one-at-a-time to control pace

## 💡 Free Tier Strategy

```python
import langextract as lx
import time

documents = [...]  # Your documents

for i, doc in enumerate(documents):
    print(f"Processing {i+1}/{len(documents)}...")
    
    result = lx.extract(
        text_or_documents=doc,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-3.6-flash",
        extraction_passes=1,      # 1 pass
        max_workers=1,            # Sequential
        max_char_buffer=10000,    # Larger chunks
    )
    
    # Save results
    lx.io.save_annotated_documents([result], ...)
    
    # Rate limit safe: ~1 request every 3-4 seconds
    if i < len(documents) - 1:
        time.sleep(4)  # Wait before next document

print("All documents processed!")
```

## ⚠️ What You're Probably Doing Wrong

❌ **Using multiple passes on free tier**
```python
result = lx.extract(..., extraction_passes=3)  # 3x requests!
```

❌ **Processing large text without adjusting chunk size**
```python
result = lx.extract("10KB text...", max_workers=5)  # Parallel chunks = 5 requests!
```

❌ **Parallel processing on free tier**
```python
result = lx.extract(..., max_workers=5)  # All 5 at once hits RPM limit
```

## ✅ What You Should Do

✓ **Keep defaults minimal**
```python
result = lx.extract(
    text_or_documents=text,
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-3.6-flash",
    # That's it! Defaults: extraction_passes=1, max_workers=5
    # But max_workers won't matter for single small text
)
```

✓ **Increase chunk size for large texts**
```python
result = lx.extract(
    text_or_documents=large_text,
    ...,
    max_char_buffer=10000,  # Reduces chunks from 4 to 1
)
```

✓ **Process multiple documents sequentially**
```python
for doc in documents:
    result = lx.extract(text_or_documents=doc, ...)
    time.sleep(2)  # Small delay between requests
```

## Summary

| Goal | Setting | Requests |
|------|---------|----------|
| **Minimum** | `extraction_passes=1, max_workers=1` | 1 per small doc |
| **Balanced** | Default for < 5KB | 1 per doc |
| **High Quality** | `extraction_passes=3, max_workers=5` | 3-15 per doc |

For free tier: **Stay with "Minimum" or "Balanced"** settings.
