import mmap
import os
import struct
import warnings
from collections import deque
from pathlib import Path
from typing import Any, Optional, Union

# Type alias for token dictionary for clarity
Token = dict[str, Any]


class Medie:
    # Magic number for MeCab dictionary files
    # from https://github.com/taku910/mecab/blob/61b90ba6e669dc2d7d533d4a80d206f3b31d52b1/mecab/src/dictionary.cpp#L25
    MAGIC_NUMBER = 0xEF718F77
    # Start offset of Double-Array (usually 72 bytes)
    DA_OFFSET_DEFAULT = 72

    mm: mmap.mmap

    # Attributes initialized in _load
    version: int
    lex_size: int
    dsize: int
    tbsize: int
    fsize: int
    da_offset: int
    token_offset: int
    feature_offset: int
    token_size: int
    charset: str

    def __init__(self, dic_path: Union[str, Path]) -> None:
        """
        Initializes the Medie object.

        :param dic_path: Path to the MeCab dictionary file.
        :type dic_path: str | Path
        """
        self.dic_path = dic_path

        self._load()

    def _load(self) -> None:
        """
        Memory-map the dictionary file and calculate offsets for each region.

        :raises FileNotFoundError: If the dictionary file is not found.
        :raises Exception: If the dictionary file is corrupted.
        """
        if not Path.exists(Path(self.dic_path)):
            raise FileNotFoundError(f"Not found: {self.dic_path}")

        # Open and mmap the file
        with open(self.dic_path, "rb") as f:
            self.mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        self.file_size = self.mm.size()

        # Header check
        magic = struct.unpack("<I", self.mm[0:4])[0]
        if (magic ^ self.MAGIC_NUMBER) != self.file_size:
            warnings.warn(f"Magic number mismatch. The dictionary file may be corrupted.")

        # Read header information
        self.version = struct.unpack("<I", self.mm[4:8])[0]
        self.lex_size = struct.unpack("<I", self.mm[12:16])[0]
        self.lsize = struct.unpack("<I", self.mm[16:20])[0]
        self.rsize = struct.unpack("<I", self.mm[20:24])[0]
        self.dsize = struct.unpack("<I", self.mm[24:28])[0]
        self.tbsize = struct.unpack("<I", self.mm[28:32])[0]
        self.fsize = struct.unpack("<I", self.mm[32:36])[0]

        # --- Get character code information from the dictionary file ---
        charset_bytes = self.mm[40:72]
        try:
            # ASCII decode and remove NULL characters
            self.charset = charset_bytes.decode("ascii").strip("\x00")
        except UnicodeDecodeError:
            # Fallback
            self.charset = "utf-8"

        # Adjust for compatibility with Python's encoding names
        if self.charset.upper() == "SHIFT-JIS":
            self.charset = "cp932"  # Consider Windows environment, etc.
        elif self.charset.upper() == "EUC-JP":
            self.charset = "euc-jp"
        elif self.charset.upper() == "UTF-8" or self.charset.upper() == "UTF8":
            self.charset = "utf-8"

        # Offset calculation (initial value)
        self.da_offset = self.DA_OFFSET_DEFAULT
        self.token_offset = self.da_offset + (self.dsize * 8)
        self.feature_offset = self.token_offset + self.tbsize

        # Token size calculation (usually 16 bytes, but varies depending on the dictionary)
        if self.lex_size > 0:
            self.token_size = self.tbsize // self.lex_size
        else:
            self.token_size = 16

        # --- Automatic offset correction ---
        expected_size = self.feature_offset + self.fsize

        if self.file_size != expected_size:
            # Recalculate offset based on the end of the file
            recalc_feature_offset = self.file_size - self.fsize
            recalc_token_offset = recalc_feature_offset - self.tbsize

            if recalc_token_offset >= self.da_offset:
                self.token_offset = recalc_token_offset
                self.feature_offset = recalc_feature_offset
            else:
                raise Exception("Offset recalculation failed. "
                                "The dictionary file may be corrupted.")

    def __del__(self) -> None:
        """Closes the memory-mapped file."""
        self.close()

    def close(self) -> None:
        """Closes the memory-mapped file."""
        if not Path.exists(Path(self.dic_path)):
            pass
        elif not self.mm.closed:
            self.mm.close()

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the context manager and close the file."""
        self.close()

    def __len__(self) -> int:
        """
        Return the number of tokens in the lexicon.

        :return: The number of tokens.
        :rtype: int
        """
        return self.lex_size

    def __repr__(self) -> str:
        """
        Return a string representation of the Medie object.

        :return: A string representation.
        :rtype: str
        """
        return (f"<Medai Path: {self.dic_path}, "
                f"Version: {self.version}, "
                f"Lexicon size: {self.lex_size}, "
                f"Left contexts: {self.lsize}, "
                f"Right contexts: {self.rsize}, "
                f"File size: {self.file_size} bytes, "
                f"Charset: {self.charset}>")

    def __hash__(self) -> int:
        """
        Return the hash of the Medai object.

        :return: The hash value.
        :rtype: int
        """
        return hash((
            self.dic_path,
            self.version,
            self.lex_size,
            self.lsize,
            self.rsize,
            self.dsize,
            self.tbsize,
            self.fsize,
            self.charset,
            self.file_size,
        ))

    def __eq__(self, other):
        """
        Check for equality with another object.

        :param other: The object to compare with.
        :return: True if equal, False otherwise.
        """
        if other is None or type(self) is not type(other):
            return False
        return hash(self) == hash(other)

    def __ne__(self, other):
        """
        Check for inequality with another object.

        :param other: The object to compare with.
        :return: True if not equal, False otherwise.
        """
        return not self.__eq__(other)

    def __contains__(self, word: str) -> bool:
        """
        Check if a word exists in the dictionary.

        :param word: The word to check.
        :type word: str
        :return: True if the word exists, False otherwise.
        :rtype: bool
        """
        try:
            bytes_key = word.encode(self.charset)
        except UnicodeEncodeError:
            return False

        return bool(self._traverse_trie(bytes_key))

    def _get_base(self, idx: int) -> int:
        """
        Get the base value from the double-array trie.

        :param idx: The index in the trie.
        :type idx: int
        :return: The base value.
        :rtype: int
        """
        pos = self.da_offset + (idx * 8)
        return struct.unpack("<i", self.mm[pos:pos + 4])[0]

    def _get_check(self, idx: int) -> int:
        """
        Get the check value from the double-array trie.

        :param idx: The index in the trie.
        :type idx: int
        :return: The check value.
        :rtype: int
        """
        pos = self.da_offset + (idx * 8) + 4
        return struct.unpack("<I", self.mm[pos:pos + 4])[0]

    def _traverse_trie(self, key: bytes) -> Optional[int]:
        """
        Traverse the Double-Array Trie with the key.

        :param key: The key to traverse with.
        :type key: bytes
        :return: The index of the end node if found, otherwise None.
        :rtype: Optional[int]
        """
        node_idx: int = 0
        for byte_val in key:
            base = self._get_base(node_idx)
            next_idx = base + byte_val + 1

            if next_idx >= self.dsize or next_idx < 0:
                return None

            check = self._get_check(next_idx)
            if check != base:
                return None

            node_idx = next_idx
        return node_idx

    def _parse_leaf_value(self, val: int) -> tuple[int, int]:
        """
        Parse the Base value of a Leaf node into Index and Count.
        Format: (Index << 8) | Count (stored as a negative value)

        :param val: The value to parse.
        :type val: int
        :return: A tuple of (index, count).
        :rtype: tuple[int, int]
        """
        val = (-val) - 1  # Invert the sign and subtract 1
        return val >> 8, val & 0xFF

    def _get_feature_string(self, offset: int) -> str:
        """
        Get the feature string from the feature area.

        :param offset: The offset of the feature string.
        :type offset: int
        :return: The feature string.
        :rtype: str
        """
        start_pos = self.feature_offset + offset
        if start_pos >= self.mm.size():
            return ""

        end_pos = self.mm.find(b"\0", start_pos)
        if end_pos == -1:
            return ""

        raw_bytes = self.mm[start_pos:end_pos]
        try:
            return raw_bytes.decode(self.charset)
        except UnicodeDecodeError:
            return raw_bytes.decode(self.charset, errors="replace")

    def _get_tokens(self, start_index: int, count: int,
                    surface: str) -> list[Token]:
        """
        Get a list of tokens.

        :param start_index: The starting index of the tokens.
        :type start_index: int
        :param count: The number of tokens to get.
        :type count: int
        :param surface: The surface form of the word.
        :type surface: str
        :return: A list of tokens.
        :rtype: list[Token]
        """
        results: list[Token] = []
        for i in range(count):
            idx = start_index + i
            pos = self.token_offset + (idx * self.token_size)

            if pos + self.token_size > self.mm.size():
                continue

            data = self.mm[pos:pos + self.token_size]

            # Read token structure
            lid, rid, _, cost, feature_offset = struct.unpack(
                "<HHHhI", data[0:12])
            feature_str = self._get_feature_string(feature_offset)

            results.append({
                "surface": surface,
                "feature": feature_str,
                "cost": cost,
                "lid": lid,  # left context ID
                "rid": rid,  # right context ID
            })
        return results

    def _retrieve_leaf_tokens(self, node_idx: int, surface: str) -> list[Token]:
        """
        If the specified node is a Leaf (end of a word), return its token list.

        :param node_idx: The index of the node.
        :type node_idx: int
        :param surface: The surface form of the word.
        :type surface: str
        :return: A list of tokens.
        :rtype: list[Token]
        """
        leaf_idx = base = self._get_base(node_idx)

        if 0 <= leaf_idx < self.dsize and self._get_check(leaf_idx) == base:
            val = self._get_base(leaf_idx)

            # Confirm that the Base value is negative (a negative value represents the value)
            if val < 0:
                index, count = self._parse_leaf_value(val)
                # Minimum check to see if the index is within the dictionary size
                if 0 <= index < self.lex_size:
                    return self._get_tokens(index, count, surface)
        return []

    def search(self, word: str, limit: int = 1) -> list[Token]:
        """
        Exact match search: Returns only words that exactly match the input.

        :param word: The word to search for.
        :type word: str
        :param limit: The maximum number of tokens to return. (default: 1)
        :type limit: int
        :return: A list of tokens.
        :rtype: list[Token]
        """
        try:
            bytes_key = word.encode(self.charset)
        except UnicodeEncodeError:
            return []

        node_idx = self._traverse_trie(bytes_key)

        if node_idx is None:
            return []

        candidates = self._retrieve_leaf_tokens(node_idx, word)

        return candidates[:limit]

    def search_prefix(self, prefix: str, limit: int = 5) -> list[Token]:
        """
        Prefix search: Returns words that start with the specified prefix.
        Duplicates (same notation, part of speech, cost, etc.) are excluded.

        :param prefix: The prefix to search for.
        :type prefix: str
        :param limit: The maximum number of tokens to return. (default: 5)
        :type limit: int
        :return: A list of tokens.
        :rtype: list[Token]
        """
        try:
            bytes_key = prefix.encode(self.charset)
        except UnicodeEncodeError:
            return []

        node_idx = self._traverse_trie(bytes_key)

        if node_idx is None:
            return []

        results: list[Token] = []
        stack: deque[tuple[int, bytes]] = deque([(node_idx, bytes_key)])

        while stack and (not limit or len(results) < limit):
            current_node, current_path = stack.popleft(
            )  # FIFO for BFS-like order

            # A. Check if this node itself is the end of a word (Leaf)
            try:
                surface = current_path.decode(self.charset)
                leaf_tokens = self._retrieve_leaf_tokens(current_node, surface)

                if leaf_tokens:
                    for token in leaf_tokens:
                        if not token["surface"].startswith(prefix):
                            continue
                        results.append(token)
                        if len(results) >= limit:
                            break
                if len(results) >= limit:
                    break
            except UnicodeDecodeError:
                # Even if current_path is not a valid string, child nodes may exist
                pass

            # B. Explore child nodes and add them to the stack
            current_base = self._get_base(current_node)
            for code in range(0x00, 0xFF + 1):
                next_idx = current_base + code + 1
                if (0 <= next_idx < self.dsize
                        and self._get_check(next_idx) == current_base):
                    new_path = current_path + bytes([code])
                    stack.append((next_idx, new_path))

        return results[:limit]
