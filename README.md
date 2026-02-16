# Medie

[![PyPI - Version](https://img.shields.io/pypi/v/medie)](https://pypi.org/project/medie/)![PyPI - Python Version](https://img.shields.io/pypi/pyversions/medie)[![PyPI - License](https://img.shields.io/pypi/l/medie)](https://github.com/ikegami-yukino/medie/blob/master/LICENSE)

Medie is a pure-Python reader for MeCab's Double-Array Trie dictionary format.

It looks up entries in MeCab dictionary files (`.dic`) by exact match or by prefix.
Medie uses `mmap` for efficient, low-memory lookups.

## Installation

```sh
python -m pip install medie
```

## Usage

### Python library

```python
from medie import Medie

medie = Medie(dic_path="path_to_sys.dic")
tokens = medie.search("私")  # Exact search
tokens
# => [{'surface': '私', 'feature': '接頭詞,名詞接続,*,*,*,*,私,シ,シ', 'cost': 9771, 'lid': 560, 'rid': 560}]

tokens = medie.search("私", limit=3)  # Specify number of search results
tokens
# => [{'surface': '私', 'feature': '接頭詞,名詞接続,*,*,*,*,私,シ,シ', 'cost': 9771, 'lid': 560, 'rid': 560}, {'surface': '私', 'feature': '名詞,代名詞,一般,*,*,*,私,ワタシ,ワタシ', 'cost': 3480, 'lid': 1306, 'rid': 1306}, {'surface': '私', 'feature': '名詞,代名詞,一般,*,*,*,私,ワタクシ,ワタクシ', 'cost': 7802, 'lid': 1306, 'rid': 1306}]

tokens = medie.search_prefix("群馬")  # Common prefix search (default value of `limit`: 5)
print(tokens)
# => [{'surface': '群馬', 'feature': '名詞,固有名詞,地域,一般,*,*,群馬,グンマ,グンマ', 'cost': 7489, 'lid': 1293, 'rid': 1293}, {'surface': '群馬大', 'feature': '名詞,固有名詞,組織,*,*,*,群馬大,グンマダイ,グンマダイ', 'cost': 6832, 'lid': 1292, 'rid': 1292}, {'surface': '群馬岳', 'feature': '名詞,固有名詞,一般,*,*,*,群馬岳,グンマタケ,グンマタケ', 'cost': 8538, 'lid': 1288, 'rid': 1288}, {'surface': '群馬八幡', 'feature': '名詞,固有名詞,一般,*,*,*,群馬八幡,グンマヤワタ,グンマヤワタ', 'cost': 8538, 'lid': 1288, 'rid': 1288}, {'surface': '群馬原町', 'feature': '名詞,固有名詞,一般,*,*,*,群馬原町,グンマハラマチ,グンマハラマチ', 'cost': 8538, 'lid': 1288, 'rid': 1288}]

tokens = medie.search_prefix("群馬", limit=3)  # Also, search_prefix API have `limit` parameter.
print(tokens)
# => [{'surface': '群馬', 'feature': '名詞,固有名詞,地域,一般,*,*,群馬,グンマ,グンマ', 'cost': 7489, 'lid': 1293, 'rid': 1293}, {'surface': '群馬大', 'feature': '名詞,固有名詞,組織,*,*,*,群馬大,グンマダイ,グンマダイ', 'cost': 6832, 'lid': 1292, 'rid': 1292}, {'surface': '群馬岳', 'feature': '名詞,固有名詞,一般,*,*,*,群馬岳,グンマタケ,グンマタケ', 'cost': 8538, 'lid': 1288, 'rid': 1288}]

with Medie(dic_path="path_to_sys.dic") as medie:  # support `with` clause
    pass
```

#### Tips

If you specify the correct dictionary but the result is empty, specifying the character encoding may solve the problem.

```python
with Medie(dic_path="path_to_sys.dic") as medie:
    medie.charset = "utf8"
```

### Command Line Interface (CLI)

`medie` or `python -m medie`

| Parameter     |  Type |  Default value |  Description                           |
|---------------|-------|----------------|----------------------------------------|
|  `--dicpath`  |  str  |                |  Path to the "sys.dic" (Required)      |
|  `--prefix`   |       |                |  Enable prefix search.                 |
|  `--limit`    |  int  |  10            |  Limit number of results.              |
|  `--charset`  |  str  |                |  Specify the charset of the "sys.dic"  |

#### Example: Exact match

```sh
echo 群馬 | medie --dicpath path_to_sys.dic
群馬,1293,1293,7489,名詞,固有名詞,地域,一般,*,*,群馬,グンマ,グンマ
```

#### Example: Prefix search

```sh
echo 群馬 | medie --dicpath path_to_sys.dic --prefix --limit 3
群馬,1293,1293,7489,名詞,固有名詞,地域,一般,*,*,群馬,グンマ,グンマ
群馬大,1292,1292,6832,名詞,固有名詞,組織,*,*,*,群馬大,グンマダイ,グンマダイ
群馬岳,1288,1288,8538,名詞,固有名詞,一般,*,*,*,群馬岳,グンマタケ,グンマタケ
```

## License

MIT license

## CHANGES

### 0.1.2 (2026-10-19)

Initial release.
