import json
import sys
from pathlib import Path
from typing import List, Optional

import typer as ty

from astchunk import ASTChunkBuilder
from astchunk.repo_scan import (
    collect_source_files,
    load_gitignore_spec,
    resolve_ignore_root,
)

app = ty.Typer(help="AST-based code chunking CLI")

SUPPORTED_LANGUAGES = frozenset({"python", "java", "csharp", "typescript"})
CHUNK_STRATEGIES = frozenset({"size", "definition", "hybrid"})


def _write_chunk_output(
    chunks: list,
    json_output: bool,
    output_file: Optional[Path],
    max_chunk_size: int,
) -> None:
    if json_output:
        output = json.dumps(chunks, indent=2)
        if output_file:
            output_file.write_text(output, encoding="utf-8")
            ty.echo(f"Wrote {len(chunks)} chunks to {output_file}", err=True)
        else:
            ty.echo(output)
    else:
        lines = []
        lines.append(
            f"AST Chunking Results (max {max_chunk_size} non-whitespace chars per chunk)"
        )
        lines.append("=" * 80)
        lines.append("")

        for i, ch in enumerate(chunks, 1):
            content = ch.get("content", ch.get("context", ""))
            metadata = ch.get("metadata", {})
            line_count = len(content.split("\n"))

            header = (
                f"{'-' * 25} Chunk {i} ({line_count} lines / "
                f"{metadata.get('chunk_size', 0)} chars) {'-' * 25}"
            )
            lines.append(header)
            lines.append(content)
            lines.append("-" * (len(header)))
            lines.append("")

        output = "\n".join(lines)

        if output_file:
            output_file.write_text(output, encoding="utf-8")
            ty.echo(f"Wrote {len(chunks)} chunks to {output_file}")
        else:
            ty.echo(output)


@app.command()
def chunk(
    input_file: Path = ty.Argument(
        ...,
        help="Input file containing source code to chunk",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output_file: Optional[Path] = ty.Option(
        None,
        "-o",
        "--output",
        help="Output file for chunks (optional, prints to stdout if not specified)",
        file_okay=True,
        dir_okay=False,
    ),
    max_chunk_size: int = ty.Option(
        1800,
        "-m",
        "--max-chunk-size",
        help="Maximum non-whitespace characters per chunk",
    ),
    language: str = ty.Option(
        "python",
        "-l",
        "--language",
        help="Programming language (python, java, csharp, typescript)",
    ),
    metadata_template: str = ty.Option(
        "default",
        "-t",
        "--metadata-template",
        help="Metadata template to use",
    ),
    chunk_expansion: bool = ty.Option(
        False,
        "-e",
        "--chunk-expansion",
        help="Enable chunk expansion with metadata headers",
    ),
    chunk_overlap: int = ty.Option(
        450,
        "--chunk-overlap",
        help="Number of AST nodes to overlap between chunks",
    ),
    repo_name: Optional[str] = ty.Option(
        None,
        "--repo-name",
        help="Repository name for metadata",
    ),
    filepath: Optional[str] = ty.Option(
        None,
        "--filepath",
        "--file-path",
        help="Override filepath in chunk metadata (default: absolute path of input file)",
    ),
    chunk_strategy: str = ty.Option(
        "size",
        "--chunk-strategy",
        help="size (default), definition (one window per top-level def), or hybrid (split large defs)",
    ),
    json_output: bool = ty.Option(
        False,
        "-j",
        "--json",
        help="Output as JSON instead of human-readable format",
    ),
):
    """
    Chunk source code into AST-based chunks.
    """
    if chunk_strategy not in CHUNK_STRATEGIES:
        raise ty.BadParameter(
            f"chunk_strategy must be one of {', '.join(sorted(CHUNK_STRATEGIES))}"
        )
    code = input_file.read_text(encoding="utf-8")

    configs = {
        "max_chunk_size": max_chunk_size,
        "language": language,
        "metadata_template": metadata_template,
        "chunk_expansion": chunk_expansion,
        "chunk_overlap": chunk_overlap,
        "chunk_strategy": chunk_strategy,
    }

    repo_level_metadata: dict = {}
    if repo_name:
        repo_level_metadata["repo_name"] = repo_name
    repo_level_metadata["filepath"] = filepath or str(input_file.resolve())

    configs["repo_level_metadata"] = repo_level_metadata

    chunk_builder = ASTChunkBuilder(**configs)
    chunks = chunk_builder.chunkify(code, **configs)

    _write_chunk_output(chunks, json_output, output_file, max_chunk_size)
    ty.echo(
        f"Created {len(chunks)} chunks",
        err=bool(json_output and output_file is None),
    )


@app.command("chunk-repo")
def chunk_repo(
    root: Path = ty.Argument(
        ...,
        help="Root directory to scan recursively",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_file: Optional[Path] = ty.Option(
        None,
        "-o",
        "--output",
        help="Output file (recommended for large repos)",
        file_okay=True,
        dir_okay=False,
    ),
    max_chunk_size: int = ty.Option(
        1800,
        "-m",
        "--max-chunk-size",
        help="Maximum non-whitespace characters per chunk",
    ),
    language: str = ty.Option(
        "auto",
        "-l",
        "--language",
        help="auto (detect from extension) or python|java|csharp|typescript",
    ),
    metadata_template: str = ty.Option(
        "default",
        "-t",
        "--metadata-template",
        help="Metadata template to use",
    ),
    chunk_expansion: bool = ty.Option(
        False,
        "-e",
        "--chunk-expansion",
        help="Enable chunk expansion with metadata headers",
    ),
    chunk_overlap: int = ty.Option(
        450,
        "--chunk-overlap",
        help="Number of AST nodes to overlap between chunks",
    ),
    repo_name: Optional[str] = ty.Option(
        None,
        "--repo-name",
        help="Repository name for metadata",
    ),
    no_gitignore: bool = ty.Option(
        False,
        "--no-gitignore",
        help="Do not filter paths using .gitignore",
    ),
    ignore_root: Optional[Path] = ty.Option(
        None,
        "--ignore-root",
        help="Directory whose .gitignore applies (default: git root or scan root)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    fail_fast: bool = ty.Option(
        False,
        "--fail-fast",
        help="Stop on the first file that fails to chunk",
    ),
    extra_ignore: List[str] = ty.Option(
        [],
        "--extra-ignore",
        help="Additional gitignore-style lines (repeatable)",
    ),
    chunk_strategy: str = ty.Option(
        "size",
        "--chunk-strategy",
        help="size (default), definition (one window per top-level def), or hybrid (split large defs)",
    ),
    json_output: bool = ty.Option(
        True,
        "--json/--no-json",
        help="Emit JSON (default for chunk-repo)",
    ),
):
    """
    Recursively chunk supported source files under a directory, honoring .gitignore.
    """
    if chunk_strategy not in CHUNK_STRATEGIES:
        raise ty.BadParameter(
            f"chunk_strategy must be one of {', '.join(sorted(CHUNK_STRATEGIES))}"
        )
    lang_filter: Optional[str]
    if language == "auto":
        lang_filter = None
    elif language in SUPPORTED_LANGUAGES:
        lang_filter = language
    else:
        raise ty.BadParameter(
            f"language must be auto or one of {', '.join(sorted(SUPPORTED_LANGUAGES))}"
        )

    ir = resolve_ignore_root(root, ignore_root)
    use_gitignore = not no_gitignore
    spec = (
        None
        if no_gitignore
        else load_gitignore_spec(ir, extra_ignore if extra_ignore else None)
    )

    files = collect_source_files(
        root.resolve(),
        ir,
        spec,
        use_gitignore=use_gitignore,
        language=lang_filter,
    )

    base_builder_kwargs = {
        "max_chunk_size": max_chunk_size,
        "metadata_template": metadata_template,
    }
    chunkify_kwargs_template = {
        "chunk_expansion": chunk_expansion,
        "chunk_overlap": chunk_overlap,
        "chunk_strategy": chunk_strategy,
    }

    builders: dict[str, ASTChunkBuilder] = {}
    all_chunks: list = []
    errors = 0

    for path, lang in files:
        builder = builders.get(lang)
        if builder is None:
            builder = ASTChunkBuilder(language=lang, **base_builder_kwargs)
            builders[lang] = builder

        repo_level_metadata: dict = {
            "filepath": str(path.resolve()),
        }
        if repo_name:
            repo_level_metadata["repo_name"] = repo_name

        run_configs = {
            **base_builder_kwargs,
            "language": lang,
            "metadata_template": metadata_template,
            **chunkify_kwargs_template,
            "repo_level_metadata": repo_level_metadata,
        }

        try:
            code = path.read_text(encoding="utf-8", errors="replace")
            file_chunks = builder.chunkify(code, **run_configs)
        except Exception as exc:  # noqa: BLE001 — per-file isolation
            errors += 1
            print(f"chunk-repo: skip {path}: {exc}", file=sys.stderr)
            if fail_fast:
                raise ty.Exit(code=1) from exc
            continue

        all_chunks.extend(file_chunks)

    _write_chunk_output(all_chunks, json_output, output_file, max_chunk_size)
    ty.echo(
        f"Created {len(all_chunks)} chunks from {len(files)} files"
        + (f" ({errors} files failed)" if errors else ""),
        err=bool(json_output and output_file is None),
    )


if __name__ == "__main__":
    app()
