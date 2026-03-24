"""Tests for tree-sitter symbol metadata and definition/hybrid chunk strategies."""

import pytest

from stump import ASTChunkBuilder


def test_default_metadata_includes_symbols_single_function() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=500,
        language="python",
        metadata_template="default",
    )
    code = "def f():\n    return 1\n"
    chunks = builder.chunkify(code, chunk_overlap=0, repo_level_metadata={"filepath": "m.py"})
    assert len(chunks) == 1
    meta = chunks[0]["metadata"]
    assert meta["symbols"] == ["f"]
    assert meta["symbol_count"] == 1


def test_symbols_multi_function_size_strategy() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=2000,
        language="python",
        metadata_template="default",
    )
    code = (
        "def alpha():\n    return 1\n\n"
        "def beta():\n    return 2\n"
    )
    chunks = builder.chunkify(code, chunk_overlap=0, repo_level_metadata={})
    assert len(chunks) == 1
    assert set(chunks[0]["metadata"]["symbols"]) == {"alpha", "beta"}
    assert chunks[0]["metadata"]["symbol_count"] == 2


def test_symbols_partial_overlap_when_chunk_splits() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=25,
        language="python",
        metadata_template="default",
    )
    code = (
        "def first():\n"
        "    return 1\n\n"
        "def second():\n"
        "    return 2\n"
    )
    chunks = builder.chunkify(code, chunk_overlap=0, repo_level_metadata={})
    assert len(chunks) >= 2
    all_syms = [set(c["metadata"]["symbols"]) for c in chunks]
    assert any("first" in s and "second" not in s for s in all_syms)
    assert any("second" in s for s in all_syms)


def test_definition_strategy_one_chunk_per_top_level_def() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=500,
        language="python",
        metadata_template="default",
    )
    code = (
        "def a():\n    return 1\n\n"
        "def b():\n    return 2\n"
    )
    chunks = builder.chunkify(
        code,
        chunk_overlap=0,
        chunk_strategy="definition",
        repo_level_metadata={},
    )
    assert len(chunks) == 2
    assert chunks[0]["metadata"]["symbols"] == ["a"]
    assert chunks[1]["metadata"]["symbols"] == ["b"]


def test_definition_strategy_with_preamble() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=500,
        language="python",
        metadata_template="default",
    )
    code = (
        "MODULE = 1\n\n"
        "def fn():\n    pass\n"
    )
    chunks = builder.chunkify(
        code,
        chunk_overlap=0,
        chunk_strategy="definition",
        repo_level_metadata={},
    )
    assert len(chunks) == 2
    assert chunks[0]["metadata"]["symbols"] == []
    assert chunks[1]["metadata"]["symbols"] == ["fn"]


def test_hybrid_splits_oversized_definition() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=400,
        language="python",
        metadata_template="default",
    )
    body = "\n".join(f"    x_{i} = {i}" for i in range(120))
    code = f"def big():\n{body}\n    return 0\n"
    chunks_def = builder.chunkify(
        code,
        chunk_overlap=0,
        chunk_strategy="definition",
        repo_level_metadata={},
    )
    chunks_hybrid = builder.chunkify(
        code,
        chunk_overlap=0,
        chunk_strategy="hybrid",
        repo_level_metadata={},
    )
    assert len(chunks_def) == 1
    assert len(chunks_hybrid) > 1
    assert all("big" in c["metadata"]["symbols"] for c in chunks_hybrid)


def test_invalid_chunk_strategy_raises() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=100,
        language="python",
        metadata_template="default",
    )
    with pytest.raises(ValueError, match="chunk_strategy"):
        builder.chunkify("x = 1\n", chunk_strategy="nope")


def test_metadata_none_has_no_symbols_key() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=500,
        language="python",
        metadata_template="none",
    )
    chunks = builder.chunkify("def f():\n    pass\n", chunk_overlap=0)
    assert chunks[0]["metadata"] == {}


def test_chunk_strategy_size_explicit() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=500,
        language="python",
        metadata_template="default",
    )
    code = "def a():\n    pass\n"
    chunks = builder.chunkify(
        code,
        chunk_strategy="size",
        repo_level_metadata={},
    )
    assert len(chunks) == 1
    assert chunks[0]["metadata"]["symbols"] == ["a"]


def test_go_definition_strategy() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=500,
        language="go",
        metadata_template="default",
    )
    code = (
        "package main\n\n"
        "func Alpha() {}\n\n"
        "func Beta() {}\n"
    )
    chunks = builder.chunkify(
        code,
        chunk_overlap=0,
        chunk_strategy="definition",
        repo_level_metadata={},
    )
    # package_clause is preamble (same pattern as Python module-level assigns).
    assert len(chunks) == 3
    assert chunks[0]["metadata"]["symbols"] == []
    assert chunks[1]["metadata"]["symbols"] == ["Alpha"]
    assert chunks[2]["metadata"]["symbols"] == ["Beta"]


def test_rust_definition_strategy() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=500,
        language="rust",
        metadata_template="default",
    )
    code = "fn alpha() {}\n\nfn beta() {}\n"
    chunks = builder.chunkify(
        code,
        chunk_overlap=0,
        chunk_strategy="definition",
        repo_level_metadata={},
    )
    assert len(chunks) == 2
    assert chunks[0]["metadata"]["symbols"] == ["alpha"]
    assert chunks[1]["metadata"]["symbols"] == ["beta"]


def test_javascript_definition_strategy() -> None:
    builder = ASTChunkBuilder(
        max_chunk_size=500,
        language="javascript",
        metadata_template="default",
    )
    code = "function alpha() {}\n\nfunction beta() {}\n"
    chunks = builder.chunkify(
        code,
        chunk_overlap=0,
        chunk_strategy="definition",
        repo_level_metadata={},
    )
    assert len(chunks) == 2
    assert chunks[0]["metadata"]["symbols"] == ["alpha"]
    assert chunks[1]["metadata"]["symbols"] == ["beta"]
