from langchain_app.vectorstore import store


def test_source_hash_changes_when_embedding_content_changes(tmp_path, monkeypatch):
    embedding_dir = tmp_path / "embedding"
    embedding_dir.mkdir()
    doc = embedding_dir / "db_diagrams.md"
    doc.write_text("## Table: sales\noriginal content", encoding="utf-8")
    monkeypatch.setattr(store, "_EMBEDDING_DIR", embedding_dir)

    first_hash = store._source_hash()

    doc.write_text("## Table: sales\nedited content", encoding="utf-8")
    second_hash = store._source_hash()

    assert first_hash != second_hash


def test_source_hash_ignores_readme(tmp_path, monkeypatch):
    embedding_dir = tmp_path / "embedding"
    embedding_dir.mkdir()
    (embedding_dir / "db_diagrams.md").write_text("content", encoding="utf-8")
    monkeypatch.setattr(store, "_EMBEDDING_DIR", embedding_dir)

    before = store._source_hash()
    (embedding_dir / "README.md").write_text("meta doc, not indexed", encoding="utf-8")
    after = store._source_hash()

    assert before == after


def test_index_is_stale_when_hash_file_missing(tmp_path, monkeypatch):
    embedding_dir = tmp_path / "embedding"
    embedding_dir.mkdir()
    (embedding_dir / "db_diagrams.md").write_text("content", encoding="utf-8")
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    monkeypatch.setattr(store, "_EMBEDDING_DIR", embedding_dir)
    monkeypatch.setattr(store, "_INDEX_DIR", index_dir)

    assert store._index_is_stale() is True


def test_index_is_not_stale_when_hash_matches(tmp_path, monkeypatch):
    embedding_dir = tmp_path / "embedding"
    embedding_dir.mkdir()
    (embedding_dir / "db_diagrams.md").write_text("content", encoding="utf-8")
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    monkeypatch.setattr(store, "_EMBEDDING_DIR", embedding_dir)
    monkeypatch.setattr(store, "_INDEX_DIR", index_dir)
    (index_dir / store._SOURCE_HASH_FILE_NAME).write_text(store._source_hash(), encoding="utf-8")

    assert store._index_is_stale() is False


def test_index_is_stale_after_content_edit(tmp_path, monkeypatch):
    embedding_dir = tmp_path / "embedding"
    embedding_dir.mkdir()
    doc = embedding_dir / "db_diagrams.md"
    doc.write_text("content", encoding="utf-8")
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    monkeypatch.setattr(store, "_EMBEDDING_DIR", embedding_dir)
    monkeypatch.setattr(store, "_INDEX_DIR", index_dir)
    (index_dir / store._SOURCE_HASH_FILE_NAME).write_text(store._source_hash(), encoding="utf-8")

    doc.write_text("edited content", encoding="utf-8")

    assert store._index_is_stale() is True


def test_load_persisted_index_returns_none_when_stale(tmp_path, monkeypatch):
    embedding_dir = tmp_path / "embedding"
    embedding_dir.mkdir()
    (embedding_dir / "db_diagrams.md").write_text("content", encoding="utf-8")
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    (index_dir / "index.faiss").write_bytes(b"stale-fake-index-bytes")
    monkeypatch.setattr(store, "_EMBEDDING_DIR", embedding_dir)
    monkeypatch.setattr(store, "_INDEX_DIR", index_dir)
    # No hash file written -> _index_is_stale() is True -> should not attempt to load

    assert store._load_persisted_index() is None
