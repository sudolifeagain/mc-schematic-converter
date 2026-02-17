"""Sponge Schematic v3 to v2 structural converter.

Sponge Schematic v3 (introduced 2021, used by WorldEdit 7.3+) restructured
the NBT layout compared to v2 (used by WorldEdit 7.2.x):

  v3 structure:
    Root("") -> Schematic -> Version, Blocks -> {Palette, Data, BlockEntities}
    BlockEntity: {Id, Pos, Data: {id, Items, ...}}
    Item: {id, count(Int), Slot, components}

  v2 structure:
    Root("Schematic") -> Version, Palette, PaletteMax, BlockData, BlockEntities
    BlockEntity: {Id, Pos, Items, ...}
    Item: {id, Count(Byte), Slot}

This module performs the structural conversion so that v3 schematics can be
loaded by WorldEdit 7.2.x (which only supports v1/v2).

Known limitations:
  - Item components (enchantments, damage, custom names) are stripped
  - Sign text format (front_text/back_text vs Text1-Text4) is not converted
  - Blocks/items not present in the target MC version become air/are lost
  - Entities require //copy -e at creation time; this converter does not add them
"""

import gzip

from .nbt import NBTReader, NBTWriter, find_tag


def _convert_item(item_entries: list) -> list:
    """Convert a single item's tags from 1.21+ to 1.20.1 format.

    - count (Int, tag 3) -> Count (Byte, tag 1)
    - components compound is removed
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


def _convert_items_list(items_val: tuple) -> tuple:
    """Convert all items in an Items list tag."""
    if items_val[0] != 'list':
        return items_val
    new_items = []
    for item in items_val[2]:
        if item[0] == 'compound':
            new_items.append(('compound', _convert_item(item[1])))
        else:
            new_items.append(item)
    return ('list', items_val[1], new_items)


# Paper/Bukkit/Spigot specific tags incompatible with Forge
_PAPER_TAGS = frozenset({
    'Paper.SpawnReason', 'Paper.Origin', 'Paper.OriginWorld', 'Paper.ShouldBurnInDay',
    'Bukkit.updateLevel', 'Bukkit.Aware', 'Spigot.ticksLived',
    'WorldUUIDMost', 'WorldUUIDLeast',
})


def _convert_entity_nbt(entries: list) -> list:
    """Convert entity NBT from 1.21+ to 1.20.1 format.

    - block_pos (IntArray[3]) -> TileX, TileY, TileZ (separate Int tags)
    - Item compound: count->Count, strip components
    - Strip Paper/Bukkit/Spigot specific tags
    """
    new = []
    tile_xyz = None
    for tag_type, tag_name, tag_val in entries:
        if tag_name in _PAPER_TAGS:
            continue
        if tag_name == 'block_pos' and tag_val[0] == 'int_array' and tag_val[1] == 3:
            tile_xyz = tag_val[2]
            continue
        if tag_name == 'Item' and tag_val[0] == 'compound':
            new.append((tag_type, tag_name, ('compound', _convert_item(tag_val[1]))))
            continue
        new.append((tag_type, tag_name, tag_val))
    if tile_xyz is not None:
        new.append((3, 'TileX', ('int', tile_xyz[0])))
        new.append((3, 'TileY', ('int', tile_xyz[1])))
        new.append((3, 'TileZ', ('int', tile_xyz[2])))
    return new


def _convert_block_entity_data(entries: list) -> list:
    """Convert the inner Data compound of a v3 BlockEntity.

    Processes Items lists and removes components.
    """
    new = []
    for tag_type, tag_name, tag_val in entries:
        if tag_name == 'Items' and tag_val[0] == 'list':
            new.append((tag_type, tag_name, _convert_items_list(tag_val)))
        elif tag_name == 'components':
            continue
        else:
            new.append((tag_type, tag_name, tag_val))
    return new


def convert_v3_to_v2(input_path: str, output_path: str) -> None:
    """Convert a Sponge Schematic v3 file to v2 format.

    Steps:
      1. Unwrap root: Root("") -> Schematic -> ... => Root("Schematic") -> ...
      2. Expand Blocks compound: Palette, Data->BlockData, BlockEntities
      3. Flatten BlockEntity Data compounds
      4. Convert item format: count(Int)->Count(Byte), strip components
      5. Set Version=2, add PaletteMax
    """
    print(f'Input:  {input_path}')
    print(f'Output: {output_path}')

    with gzip.open(input_path, 'rb') as f:
        data = f.read()

    reader = NBTReader(data)
    root_type = reader.read_ubyte()
    root_name = reader.read_string()
    root = reader.read_payload(root_type)

    # v3: Root("") -> Schematic compound
    # v2: Root("Schematic") -> tags directly
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

        elif cn == 'Entities':
            # v3: {Id, Pos, Data: {id, Pos, Rotation, ...}}
            # v2: {Id, Pos, Rotation, ...} (Data unwrapped)
            if cv[0] == 'list' and cv[2]:
                converted_entities = []
                for entity in cv[2]:
                    if entity[0] != 'compound':
                        converted_entities.append(entity)
                        continue
                    entity_map = {ecn: (ect, ecv) for ect, ecn, ecv in entity[1]}
                    new_entry = []
                    if 'Id' in entity_map:
                        ect, ecv = entity_map['Id']
                        new_entry.append((ect, 'Id', ecv))
                    if 'Pos' in entity_map:
                        ect, ecv = entity_map['Pos']
                        new_entry.append((ect, 'Pos', ecv))
                    if 'Data' in entity_map:
                        ect, ecv = entity_map['Data']
                        if ecv[0] == 'compound':
                            for dct, dcn, dcv in ecv[1]:
                                if dcn in ('id', 'Pos'):
                                    continue
                                new_entry.append((dct, dcn, dcv))
                    new_entry = _convert_entity_nbt(new_entry)
                    converted_entities.append(('compound', new_entry))
                v2_entries.append((9, 'Entities', ('list', 10, converted_entities)))
                print(f'Entities: {len(converted_entities)} converted')
            else:
                print('Entities: 0')

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

                    if 'Data' in entity_map:
                        ect, ecv = entity_map['Data']
                        if ecv[0] == 'compound':
                            inner = _convert_block_entity_data(ecv[1])
                            for dct, dcn, dcv in inner:
                                if dcn == 'id':
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

    # Verify
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
