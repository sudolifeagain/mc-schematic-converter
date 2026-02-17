"""CLI entry point: python -m mc_schematic_converter <input> <output>"""

import sys

from .converter import convert_v3_to_v2


def main() -> None:
    if len(sys.argv) < 3:
        print(f'Usage: python -m mc_schematic_converter <input.schem> <output.schem>')
        print()
        print('Convert Sponge Schematic v3 to v2 for WorldEdit 7.2.x compatibility.')
        sys.exit(1)
    convert_v3_to_v2(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
