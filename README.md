# mc-schematic-converter

Sponge Schematic v3 を v2 に変換するツール。WorldEdit 7.2.x（MC 1.20.1 等）で v3 形式の `.schem` ファイルを読み込めるようにする。

外部依存なし。Python 3.8+ の標準ライブラリのみで動作する。

## 使用方法

```bash
# モジュールとして実行
python -m mc_schematic_converter <input.schem> <output.schem>

# pip install 後
mc-schematic-converter <input.schem> <output.schem>
```

## Sponge Schematic バージョン対応表

### 仕様バージョン

[Sponge Schematic Specification](https://github.com/SpongePowered/Schematic-Specification) で定義されている3つのバージョンが存在する。

| Sponge Schematic | 仕様策定日 | DataVersion | Entity | Biome | BlockEntity キー | Palette 配置 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **v1** | 2016-08-23 | なし | 非対応 | 非対応 | `TileEntities` | ルート直下 |
| **v2** | 2019-05-08 | あり（必須） | 対応 | 2D | `TileEntities` | ルート直下 |
| **v3** | 2021-05-04 | あり（必須） | 対応 | 3D | `BlockEntities` | `Blocks` 内にネスト |

### WorldEdit バージョンとの対応

| WorldEdit | 対応 MC | デフォルト書き出し | 読み込み対応 |
|:---:|:---:|:---:|:---:|
| 7.0.x | 1.13.2 - 1.14.x | Sponge v1 | v1 |
| 7.1.x | 1.13.2 - 1.15.x | Sponge v1 | v1 |
| **7.2.x** | 1.13.2 - 1.20.4 | **Sponge v2** | **v1, v2** |
| 7.3.x | 1.20 - 1.20.4 | Sponge v3 | v1, v2, v3 |
| 7.4.x | 1.21+ | Sponge v3 | v1, v2, v3 |

WorldEdit 7.3+ では `//schem save <name> sponge.2` で v2 書き出しを明示指定可能。

### Minecraft バージョンとの実質的な対応

Sponge Schematic 自体はバージョン非依存の仕様だが、`DataVersion` フィールドにより作成元の MC バージョンが記録される。実質的な対応は以下の通り。

| MC バージョン | DataVersion | 主な変更 |
|:---:|:---:|:---|
| 1.12.2 以前 | - | MCEdit `.schematic` 形式（数値ブロック ID） |
| 1.13 - 1.17.x | 1519 - 2860 | Flattening 以降。文字列ベースのブロック ID |
| 1.18 - 1.20.4 | 2860 - 3837 | 3D バイオーム導入（Sponge v3 が実用的に） |
| 1.20.5 - 1.21.x | 3837+ | アイテム NBT 形式変更（`components` 導入、`count` → `Count` 変更） |

## 変換内容

本ツールが行う v3 → v2 の構造変換:

| 項目 | v3 | v2 |
|:---|:---|:---|
| ルート構造 | `Root("") → Schematic → ...` | `Root("Schematic") → ...` |
| ブロックデータ | `Blocks.Data` | `BlockData` |
| パレット | `Blocks.Palette` | `Palette` + `PaletteMax` |
| BlockEntity | `Data` コンパウンドでラップ | フラット |
| アイテム個数 | `count` (Int) | `Count` (Byte) |
| Version タグ | 3 | 2 |

## 既知の制約

- アイテムの `components`（エンチャント、耐久値、カスタム名等）は削除される
- 看板テキスト形式（`front_text`/`back_text` vs `Text1`-`Text4`）は未変換
- 対象 MC バージョンに存在しないブロック/アイテムは消失する
- エンティティ（額縁、絵画等）は `//copy -e` で取得した場合のみ schematic に含まれる

## プロジェクト構成

```
mc-schematic-converter/
├── pyproject.toml
├── LICENSE
├── README.md
├── src/
│   └── mc_schematic_converter/
│       ├── __init__.py
│       ├── __main__.py        # CLI エントリーポイント
│       ├── converter.py       # v3→v2 変換ロジック
│       └── nbt.py             # NBT バイナリ読み書きライブラリ
└── tests/
```

## 参考資料

- [Sponge Schematic Specification (GitHub)](https://github.com/SpongePowered/Schematic-Specification)
- [WorldEdit Documentation](https://worldedit.enginehub.org/)
- [Minecraft Data Version (Minecraft Wiki)](https://minecraft.fandom.com/wiki/Data_version)
