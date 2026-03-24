"""Tests for repo scanning and gitignore filtering."""
from pathlib import Path

from stump.repo_scan import (
    collect_source_files,
    load_gitignore_spec,
    resolve_ignore_root,
)


def test_collect_respects_gitignore(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text("x = 1\n", encoding="utf-8")
    skip_dir = tmp_path / "skipme"
    skip_dir.mkdir()
    (skip_dir / "gone.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("skipme/\n", encoding="utf-8")

    spec = load_gitignore_spec(tmp_path)
    files = collect_source_files(
        tmp_path,
        tmp_path,
        spec,
        use_gitignore=True,
        language=None,
    )
    paths = [p for p, _ in files]
    assert len(paths) == 1
    assert paths[0].name == "keep.py"


def test_extra_ignore_patterns(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("pass\n", encoding="utf-8")
    spec = load_gitignore_spec(tmp_path, extra_patterns=["b.py"])
    files = collect_source_files(
        tmp_path,
        tmp_path,
        spec,
        use_gitignore=True,
        language=None,
    )
    assert [p.name for p, _ in files] == ["a.py"]


def test_language_filter(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text("a=1\n", encoding="utf-8")
    (tmp_path / "x.java").write_text("class X {}\n", encoding="utf-8")
    files = collect_source_files(
        tmp_path,
        tmp_path,
        None,
        use_gitignore=False,
        language="python",
    )
    assert len(files) == 1
    assert files[0][0].suffix == ".py"
    assert files[0][1] == "python"


def test_extension_language_mapping_go_rust_js(tmp_path: Path) -> None:
    (tmp_path / "a.go").write_text("package main\n", encoding="utf-8")
    (tmp_path / "b.rs").write_text("fn main() {}\n", encoding="utf-8")
    (tmp_path / "c.jsx").write_text("export default function C() {}\n", encoding="utf-8")
    (tmp_path / "d.mjs").write_text("export const x = 1\n", encoding="utf-8")
    files = collect_source_files(
        tmp_path,
        tmp_path,
        None,
        use_gitignore=False,
        language=None,
    )
    by_name = {p.name: lang for p, lang in files}
    assert by_name["a.go"] == "go"
    assert by_name["b.rs"] == "rust"
    assert by_name["c.jsx"] == "javascript"
    assert by_name["d.mjs"] == "javascript"


def test_resolve_ignore_root_override(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    assert resolve_ignore_root(sub, tmp_path) == tmp_path.resolve()


def test_path_under_git_dir_segment() -> None:
    from stump.repo_scan import _path_under_git_dir

    assert _path_under_git_dir(Path("/proj/.git/config"))
    assert not _path_under_git_dir(Path("/proj/src/main.py"))


def test_chunk_metadata_filepath_absolute(tmp_path: Path) -> None:
    from stump import ASTChunkBuilder

    src = tmp_path / "mod.py"
    src.write_text("def f():\n    return 1\n", encoding="utf-8")
    builder = ASTChunkBuilder(
        max_chunk_size=500,
        language="python",
        metadata_template="default",
    )
    chunks = builder.chunkify(
        src.read_text(encoding="utf-8"),
        chunk_overlap=0,
        repo_level_metadata={"filepath": str(src.resolve())},
    )
    assert chunks
    meta = chunks[0]["metadata"]
    assert meta["filepath"] == str(src.resolve())
    assert meta["symbols"] == ["f"]
    assert meta["symbol_count"] == 1
