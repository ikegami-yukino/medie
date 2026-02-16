from pathlib import Path

import pytest

from medie import Medie

TEST_DIR_PATH = Path(__file__).parent / Path("dic")
TEST_SYS_DIC_PATH = TEST_DIR_PATH / Path("sys.dic")
TEST_UNK_DIC_PATH = TEST_DIR_PATH / Path("unk.dic")


def test_load_file_not_found():
    """Test that FileNotFoundError is raised for a non-existent file."""
    with pytest.raises(FileNotFoundError):
        Medie("non_existent_file.dic")


def test_context_manager():
    """Test that the context manager opens and closes the file."""
    with Medie(TEST_SYS_DIC_PATH) as medie:
        assert not medie.mm.closed
    assert medie.mm.closed


def test_equality():
    """Test the equality and hash methods."""
    with Medie(TEST_SYS_DIC_PATH) as medie1:
        with Medie(TEST_SYS_DIC_PATH) as medie2:
            assert medie1 == medie2
            assert hash(medie1) == hash(medie2)

        # Different files should not be equal
        with Medie(TEST_UNK_DIC_PATH) as medie2:
            assert medie1 != medie2
            assert hash(medie1) != hash(medie2)


def test_contains():
    """Test the __contains__ method."""
    with Medie(TEST_SYS_DIC_PATH) as medie:
        assert "私" in medie
        assert "は" in medie
        assert "私事" in medie
        assert "a" not in medie
        assert "東京" not in medie  # The Trie is too simple for this


def test_search_exact_found():
    """Test exact search for a word that exists."""
    with Medie(TEST_SYS_DIC_PATH) as medie:
        tokens = medie.search("私")
        assert len(tokens) == 1
        token = tokens[0]
        assert token["surface"] == "私"
        assert token["cost"] == 3480
        assert token["lid"] == 2
        assert token["rid"] == 2
        assert "名詞,代名詞,一般,*,*,*,私,ワタシ,ワタシ" in token["feature"]


def test_search_exact_not_found():
    """Test exact search for a word that does not exist."""
    with Medie(TEST_SYS_DIC_PATH) as medie:
        tokens = medie.search("a")
        assert len(tokens) == 0


def test_search_prefix_basic():
    """Test prefix search with a simple case."""
    with Medie(TEST_SYS_DIC_PATH) as medie:
        # Our simple trie only has '私', so it should be found if we search for '私' as a prefix
        tokens = medie.search_prefix("私")
        assert len(tokens) > 0
        assert tokens[0]["surface"] == "私"
        assert tokens[1]["surface"] == "私事"

        # Searching for a prefix that doesn't lead to any word
        tokens_no_match = medie.search_prefix("a")
        assert len(tokens_no_match) == 0
