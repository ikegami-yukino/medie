# 実行コマンド備忘録

## テスト

1. tox -p # tox が入っていない場合は事前に uv tool install tox --with tox-uv

## ビルド & リリース

1. uv run python -m build
2. uv run twine check dist/*
3. uv run twine upload --repository testpypi dist/*
4. uv run twine upload dist/*
