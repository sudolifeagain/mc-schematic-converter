# mc-schematic-converter

Sponge Schematic v3 (MC 1.20.5+) を v2 (WorldEdit 7.2.x) 形式に変換するツール。

外部依存なし。Python 3.8+ の標準ライブラリのみで動作する。

## 使用方法

```bash
python convert.py <input.schem> <output.schem>
```

## 変換内容

| 項目 | v3 (1.20.5+) | v2 (7.2.x) |
|------|-------------|-------------|
| ルート構造 | `Root("") → Schematic → ...` | `Root("Schematic") → ...` |
| ブロックデータ | `Blocks.Data` | `BlockData` |
| パレット | `Blocks.Palette` | `Palette` + `PaletteMax` |
| BlockEntity | `Data` コンパウンドでラップ | フラット |
| アイテム個数 | `count` (Int) | `Count` (Byte) |
| Version | 3 | 2 |

## 既知の制約

- アイテムの `components`（エンチャント、耐久値、カスタム名等）は変換非対応。削除される
- 看板テキスト形式（`front_text`/`back_text` vs `Text1`-`Text4`）は未変換
- 1.20.1 に存在しないブロック/アイテムは消失する
- エンティティ（額縁、絵画等）は `//copy -e` で取得した場合のみ含まれる

## ファイル構成

| ファイル | 内容 |
|---------|------|
| `convert.py` | v3→v2 変換 CLI |
| `nbt.py` | NBT バイナリ読み書きライブラリ |
