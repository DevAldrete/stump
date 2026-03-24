# Stump

**Stump** is an AST-aware code chunking tool and library: it splits source using **tree-sitter** parse trees so chunks respect syntactic boundaries. The name is a nod to what is left when you “cut” a syntax tree into pieces.

This project is **actively developed by [DevAldrete](https://github.com/DevAldrete)** on top of the **ASTChunk** research codebase. Original algorithms and the scientific credit belong to the ASTChunk authors; Stump adds its own packaging, CLI, and ongoing changes. See **[NOTICE](NOTICE)** and **[LICENSE](LICENSE)** for copyright and derivative-work attribution.

### Cite the original research

The method is described in the **cAST** paper. Please cite it when you use Stump in academic work:

>[cAST: Enhancing Code Retrieval-Augmented Generation with Structural Chunking via Abstract Syntax Tree](https://arxiv.org/abs/2506.15655)    
> Yilin Zhang, Xinran Zhao, Zora Zhiruo Wang, Chenyang Yang, Jiayi Wei, Tongshuang Wu
<!--
> Conference/Journal, Year
-->

Bibtex for citations:
```bibtex
@misc{zhang-etal-2025-astchunk,
      title={cAST: Enhancing Code Retrieval-Augmented Generation with Structural Chunking via Abstract Syntax Tree}, 
      author={Yilin Zhang and Xinran Zhao and Zora Zhiruo Wang and Chenyang Yang and Jiayi Wei and Tongshuang Wu},
      year={2025},
      url={https://arxiv.org/abs/2506.15655}, 
}
```
<!--
Bibtex for citations:
```bibtex
@inproceedings{<citation_key>,
    title = "<Paper Title>",
    author = "<Authors>",
    booktitle = "<Conference>",
    year = "<Year>",
    url = "<URL>",
    pages = "<Pages>",
}
```
-->

<!--
## Features

- **Structure-aware chunking**: Respects AST boundaries to avoid breaking syntactic constructs
- **Multi-language support**: Python, Java, C#, and TypeScript
- **Configurable chunk sizes**: Based on non-whitespace character count for consistent sizing
- **Metadata preservation**: Maintains file paths, line numbers, and AST context
- **Overlapping support**: Optional overlapping between chunks for better context
- **Efficient processing**: O(1) chunk size lookup with preprocessing
-->

## Installation

From PyPI (after you publish the `stump` package):
```bash
pip install stump
```

From source:
```bash
git clone https://github.com/DevAldrete/stump.git
cd stump
pip install -e .
```

If your GitHub repository is still named differently (for example `astchunk-cli`), use that clone URL and directory name, and align `Homepage` / `Repository` in `pyproject.toml` with the real URL.

After install, the CLI is **`stump`** (`stump --help`). You can also run **`python main.py`** from the repository root when dependencies are available (the shim prepends `src/` for imports).

**Upstream library:** the original project remains at [github.com/yilinjz/astchunk](https://github.com/yilinjz/astchunk) and may publish under a different PyPI name; this line is independent.

### Docker

Build and run the CLI in a container (mount your code to chunk a directory on the host):

```bash
docker build -t stump .
docker run --rm stump --help
docker run --rm -v "$PWD":/work -w /work stump chunk-repo . -o /work/chunks.json
```

### Building wheels for PyPI

With the optional publish dependencies (`pip install '.[publish]'`), from the repo root:

```bash
python -m build
twine check dist/*
# twine upload dist/*
```

Stump depends on [tree-sitter](https://tree-sitter.github.io/tree-sitter/) for parsing. The required language parsers are installed with the package:

```bash
# Core dependencies (automatically installed)
pip install numpy pyrsistent tree-sitter
pip install tree-sitter-python tree-sitter-java tree-sitter-c-sharp tree-sitter-typescript
```

## Configuration Options

- **`max_chunk_size`**: Maximum non-whitespace characters per chunk
- **`language`**: Programming language for parsing
- **`metadata_template`**: Format for chunk metadata
- **`repo_level_metadata`** *(optional)*: Repository-level metadata (e.g., repo name, file path)
- **`chunk_overlap`** *(optional)*: Number of AST nodes to overlap between chunks
- **`chunk_expansion`** *(optional)*: Whether to perform chunk expansion (i.e., add metadata headers to chunks)
- **`chunk_strategy`** *(optional)*: `size` (default, greedy AST windows), `definition` (one top-level definition per chunk; may exceed `max_chunk_size`), or `hybrid` (definition boundaries with greedy splitting inside oversized definitions)

### Symbol metadata (`default` and `coderagbench-repoeval` templates)

Chunks include **`symbols`** (simple names) and **`symbol_count`**. A name is listed when its tree-sitter definition overlaps the chunk’s line span (inclusive). Line numbers in metadata use tree-sitter’s **0-based** row indices, matching `start_line_no` / `end_line_no`. Duplicate simple names from different scopes appear once in `symbols`.

CLI: pass `--chunk-strategy size|definition|hybrid` to `chunk` and `chunk-repo`.

## Quick Start

```python
from stump import ASTChunkBuilder

# Your source code
code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
"""

# Initialize the chunk builder
configs = {
    "max_chunk_size": 100,             # Maximum non-whitespace characters per chunk
    "language": "python",              # Supported: python, java, csharp, typescript
    "metadata_template": "default"     # Metadata format for output
}
chunk_builder = ASTChunkBuilder(**configs)

# Create chunks
chunks = chunk_builder.chunkify(code)

# Each chunk contains content and metadata
for i, chunk in enumerate(chunks):
    print(f"[Chunk {i+1}]")
    print(f"{chunk['content']}")
    print(f"Metadata: {chunk['metadata']}")
    print("-" * 50)
```

## Advanced Usage

### Customizing Chunk Parameters

```python

# Add repo-level metadata
configs['repo_level_metadata'] = {
    "filepath": "src/calculator.py"
}

# Enable overlapping between chunks
configs['chunk_overlap'] = 1

# Add chunk expansion (metadata headers)
configs['chunk_expansion'] = True

# NOTE: max_chunk_size apply to the chunks before overlapping or chunk expansion.
# The final chunk size after overlapping or chunk expansion may exceed max_chunk_size.


# Extend current code for illustration
code += """
def divide(self, a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# This is a comment
# Another comment

def subtract(self, a, b):
    return a - b

def exponent(self, a, b):
    return a ** b
"""


# Create chunks
chunks = chunk_builder.chunkify(code, **configs)

for i, chunk in enumerate(chunks):
    print(f"[Chunk {i+1}]")
    print(f"{chunk['content']}")
    print(f"Metadata: {chunk['metadata']}")
    print("-" * 50)
```

### Working with Files

```python
# Process a single file
with open("example.py", "r") as f:
    code = f.read()

# Alternatively, you can also create single-use configs for the optional arguments for each chunkify() call
single_use_configs = {
    "repo_level_metadata": {
        "filepath": "example.py"
    },
    "chunk_expansion": True
}

chunks = chunk_builder.chunkify(code, **single_use_configs)

# Save chunks to separate files
for i, chunk in enumerate(chunks):
    with open(f"chunk_{i+1}.py", "w") as f:
        f.write(chunk['content'])
```

### Processing Multiple Languages

```python
# Python code
python_builder = ASTChunkBuilder(
    max_chunk_size=1500,
    language="python",
    metadata_template="default"
)

# Java code  
java_builder = ASTChunkBuilder(
    max_chunk_size=2000,
    language="java", 
    metadata_template="default"
)

# TypeScript code
ts_builder = ASTChunkBuilder(
    max_chunk_size=1800,
    language="typescript",
    metadata_template="default"
)
```

<!-- ### Metadata Templates

Different metadata templates for various use cases:

```python
# For repoeval
repoeval_builder = ASTChunkBuilder(
    max_chunk_size=2000,
    language="python",
    metadata_template="coderagbench-repoeval"
)

# For swebench-lite
swebench_builder = ASTChunkBuilder(
    max_chunk_size=2000,
    language="python",
    metadata_template="coderagbench-swebench-lite"
)
``` -->

<!-- ## Core Functions

### Preprocessing Functions

```python
from stump.preprocessing import preprocess_nws_count, get_nws_count, ByteRange

# Preprocess code for efficient size calculation
code_bytes = code.encode('utf-8')
nws_cumsum = preprocess_nws_count(code_bytes)

# Get non-whitespace character count for any byte range
byte_range = ByteRange(0, 100)  # First 100 bytes
char_count = get_nws_count(nws_cumsum, byte_range)
```

### Direct AST Processing

```python
from stump.astnode import ASTNode
from stump.astchunk import ASTChunk

# Work directly with AST nodes and chunks for custom processing
# (See API documentation for detailed usage)
``` -->

## Supported Languages

| Language    | File Extensions | Status |
|-------------|-----------------|---------|
| Python      | `.py`           | ✅ Full support |
| Java        | `.java`         | ✅ Full support |
| C#          | `.cs`           | ✅ Full support |
| TypeScript  | `.ts`, `.tsx`   | ✅ Full support |
| Go          | `.go`           | ✅ Full support |
| Rust        | `.rs`           | ✅ Full support |
| JavaScript  | `.js`, `.jsx`, `.mjs`, `.cjs` | ✅ Full support |

<!-- ## Contributing

We welcome contributions! Please see our [contributing guidelines](<CONTRIBUTING_URL>) for details. -->

## License

[MIT License](LICENSE). Attribution for the original ASTChunk work and Stump changes is summarized in [NOTICE](NOTICE); the full legal text is in `LICENSE`.

## Version

Current version: 0.1.0
