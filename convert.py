"""Convert Sponge Schematic v3 to v2 for WorldEdit 7.2.x compatibility.

Sponge Schematic v3 (MC 1.20.5+) restructured the format:
- Root is nested under a "Schematic" compound
- Block data is nested under a "Blocks" compound
- BlockEntity NBT is wrapped in a "Data" compound
- Item format changed: count(Int) -> Count(Byte), components added

WorldEdit 7.2.x (MC 1.20.1) only reads v2. This script performs the
structural conversion to make v3 schematics loadable.

Known limitations:
- Item components (enchantments, damage, custom names) are stripped
- Sign text format (front_text/back_text vs Text1-Text4) is not converted
- Blocks/items that don't exist in 1.20.1 will be air/lost
- Entities are not included unless the schematic was created with //copy -e
"""

import gzip
import sys

from nbt import NBTReader, NBTWriter, find_tag


def convert_item(item_entries: list) -> list:
    """Convert 1.21+ item format to 1.20.1.

    - count (Int, tag 3) -> Count (Byte, tag 1)
    - components compound is removed (enchantments, damage etc. are lost)
    """
    new = []
    for tag_type, tag_name, tag_val in item_entries:
        if tag_name == 'count':
            val = min(127, max(0, tag_val[1]))
            new.append((1, 'Count', ('byte', val)))
        elif tag_name == 'components':
            continue
        else:
            new.append((tag_type, tag_name, tag_val))
    return new


def convert_items_list(items_val: tuple) -> tuple:
    """Convert all items in an Items list tag."""
    if items_val[0] != 'list':
        return items_val
    new_items = []
    for item in items_val[2]:
        if item[0] == 'compound':
            new_items.append(('compound', convert_item(item[1])))
        else:
            new_items.append(item)
    return ('list', items_val[1], new_items)


def convert_block_entity_data(entries: list) -> list:
    """Convert the inner Data compound of a BlockEntity.

    Processes Items lists and removes components.
    """
    new = []
    for tag_type, tag_name, tag_val in entries:
        if tag_name == 'Items' and tag_val[0] == 'list':
            new.append((tag_type, tag_name, convert_items_list(tag_val)))
        elif tag_name == 'components':
            continue
        else:
            new.append((tag_type, tag_name, tag_val))
    return new


def convert_v3_to_v2(input_path: str, output_path: str) -> None:
    """Convert a Sponge Schematic v3 file to v2 format.

    Conversion steps:
    1. Unwrap root structure: Root("") -> Schematic -> ... becomes Root("Schematic") -> ...
    2. Expand Blocks compound: Palette, Data->BlockData, BlockEntities to root level
    3. Unwrap BlockEntity Data compounds
    4. Convert item format: count(Int)->Count(Byte), remove components
    5. Set Version tag to 2, add PaletteMax
    """
    print(f'Input:  {input_path}')
    print(f'Output: {output_path}')

    with gzip.open(input_path, 'rb') as f:
        data = f.read()

    reader = NBTReader(data)
    root_type = reader.read_ubyte()
    root_name = reader.read_string()
    root = reader.read_payload(root_type)

    # v3: Root("") -> Schematic compound; v2: Root("Schematic") -> direct
    if root_name == '' or root_name == 'Schematic':
        _, schem = find_tag(root, 'Schematic')
        if schem is None:
            schem = root
    else:
        schem = root

    _, ver = find_tag(schem, 'Version')
    if ver:
        print(f'Source version: {ver[1]}')

    v2_entries = []
    for ct, cn, cv in schem[1]:
        if cn == 'Version':
            v2_entries.append((3, 'Version', ('int', 2)))
            print('Version -> 2')

        elif cn == 'Blocks':
            blocks = {bcn: (bct, bcv) for bct, bcn, bcv in cv[1]}

            if 'Palette' in blocks:
                bt, bv = blocks['Palette']
                v2_entries.append((bt, 'Palette', bv))
                palette_size = len(bv[1]) if bv[0] == 'compound' else 0
                v2_entries.append((3, 'PaletteMax', ('int', palette_size)))
                print(f'Palette: {palette_size} entries')

            if 'Data' in blocks:
                bt, bv = blocks['Data']
                v2_entries.append((bt, 'BlockData', bv))
                print('Blocks.Data -> BlockData')

            if 'BlockEntities' in blocks:
                bt, bv = blocks['BlockEntities']
                converted = []
                items_count = 0
                for entity in bv[2]:
                    entity_map = {ecn: (ect, ecv) for ect, ecn, ecv in entity[1]}
                    new_entry = []

                    if 'Id' in entity_map:
                        ect, ecv = entity_map['Id']
                        new_entry.append((ect, 'Id', ecv))
                    if 'Pos' in entity_map:
                        ect, ecv = entity_map['Pos']
                        new_entry.append((ect, 'Pos', ecv))

                    # Unwrap Data compound: move inner tags to parent level
                    if 'Data' in entity_map:
                        ect, ecv = entity_map['Data']
                        if ecv[0] == 'compound':
                            inner = convert_block_entity_data(ecv[1])
                            for dct, dcn, dcv in inner:
                                if dcn == 'id':  # skip lowercase id (duplicate of Id)
                                    continue
                                new_entry.append((dct, dcn, dcv))
                            if any(dcn == 'Items' for _, dcn, _ in inner):
                                items_count += 1

                    converted.append(('compound', new_entry))

                v2_entries.append((9, 'BlockEntities', ('list', 10, converted)))
                print(f'BlockEntities: {len(converted)} total, {items_count} with items')
        else:
            v2_entries.append((ct, cn, cv))

    # Write v2 with Root("Schematic")
    writer = NBTWriter()
    writer.write_ubyte(10)
    writer.write_string('Schematic')
    for ct, cn, cv in v2_entries:
        writer.write_ubyte(ct)
        writer.write_string(cn)
        writer.write_payload(ct, cv)
    writer.write_ubyte(0)

    with gzip.open(output_path, 'wb') as f:
        f.write(writer.get_bytes())
    print(f'Saved: {output_path}')

    # Verify output structure
    with gzip.open(output_path, 'rb') as f:
        verify_data = f.read()
    vr = NBTReader(verify_data)
    vr.read_ubyte()
    vrn = vr.read_string()
    print(f'Verify: root_name="{vrn}" (expect "Schematic")')
    vroot = vr.read_payload(10)
    _, vver = find_tag(vroot, 'Version')
    if vver:
        print(f'Verify: Version={vver[1]} (expect 2)')
    _, vpal = find_tag(vroot, 'Palette')
    print(f'Verify: Palette exists = {vpal is not None}')
    _, vbd = find_tag(vroot, 'BlockData')
    print(f'Verify: BlockData exists = {vbd is not None}')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f'Usage: {sys.argv[0]} <input.schem> <output.schem>')
        print()
        print('Convert Sponge Schematic v3 (MC 1.20.5+) to v2 (WorldEdit 7.2.x)')
        sys.exit(1)
    convert_v3_to_v2(sys.argv[1], sys.argv[2])
