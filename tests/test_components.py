"""Tests for item components -> legacy tag conversion."""

from mc_schematic_converter.converter import (
    _convert_components_to_tag,
    _convert_enchantments,
    _convert_item,
)


def test_convert_enchantments_basic():
    """levels compound with two enchantments -> list of {id, lvl} compounds."""
    levels = ('compound', [
        (3, 'minecraft:sharpness', ('int', 5)),
        (3, 'minecraft:unbreaking', ('int', 3)),
    ])
    result = _convert_enchantments(levels)
    assert len(result) == 2
    # First enchantment
    assert result[0][0] == 'compound'
    entries = {n: v for _, n, v in result[0][1]}
    assert entries['id'] == ('string', 'minecraft:sharpness')
    assert entries['lvl'] == ('short', 5)
    # Second enchantment
    entries2 = {n: v for _, n, v in result[1][1]}
    assert entries2['id'] == ('string', 'minecraft:unbreaking')
    assert entries2['lvl'] == ('short', 3)


def test_convert_enchantments_empty():
    levels = ('compound', [])
    assert _convert_enchantments(levels) == []


def test_convert_enchantments_non_compound():
    assert _convert_enchantments(('string', 'invalid')) == []


def test_convert_components_enchantments():
    """minecraft:enchantments -> Enchantments list in tag."""
    components = ('compound', [
        (10, 'minecraft:enchantments', ('compound', [
            (10, 'levels', ('compound', [
                (3, 'minecraft:sharpness', ('int', 5)),
            ])),
        ])),
    ])
    result = _convert_components_to_tag(components)
    assert len(result) == 1
    tag_type, tag_name, tag_val = result[0]
    assert tag_type == 9
    assert tag_name == 'Enchantments'
    assert tag_val[0] == 'list'
    assert tag_val[1] == 10
    assert len(tag_val[2]) == 1


def test_convert_components_enchantments_direct():
    """minecraft:enchantments without levels wrapper (Paper format)."""
    components = ('compound', [
        (10, 'minecraft:enchantments', ('compound', [
            (3, 'minecraft:unbreaking', ('int', 3)),
            (3, 'minecraft:efficiency', ('int', 4)),
        ])),
    ])
    result = _convert_components_to_tag(components)
    assert len(result) == 1
    tag_type, tag_name, tag_val = result[0]
    assert tag_name == 'Enchantments'
    assert len(tag_val[2]) == 2
    entries = {e[1][0][2][1]: e[1][1][2][1] for e in tag_val[2]}
    assert entries['minecraft:unbreaking'] == 3
    assert entries['minecraft:efficiency'] == 4


def test_convert_components_stored_enchantments():
    """minecraft:stored_enchantments -> StoredEnchantments (enchanted books)."""
    components = ('compound', [
        (10, 'minecraft:stored_enchantments', ('compound', [
            (10, 'levels', ('compound', [
                (3, 'minecraft:protection', ('int', 4)),
            ])),
        ])),
    ])
    result = _convert_components_to_tag(components)
    names = {n for _, n, _ in result}
    assert 'StoredEnchantments' in names


def test_convert_components_damage():
    components = ('compound', [
        (3, 'minecraft:damage', ('int', 100)),
    ])
    result = _convert_components_to_tag(components)
    assert len(result) == 1
    assert result[0] == (3, 'Damage', ('int', 100))


def test_convert_components_repair_cost():
    components = ('compound', [
        (3, 'minecraft:repair_cost', ('int', 7)),
    ])
    result = _convert_components_to_tag(components)
    assert result[0] == (3, 'RepairCost', ('int', 7))


def test_convert_components_custom_model_data():
    components = ('compound', [
        (3, 'minecraft:custom_model_data', ('int', 42)),
    ])
    result = _convert_components_to_tag(components)
    assert result[0] == (3, 'CustomModelData', ('int', 42))


def test_convert_components_unbreakable():
    components = ('compound', [
        (10, 'minecraft:unbreakable', ('compound', [])),
    ])
    result = _convert_components_to_tag(components)
    assert result[0] == (1, 'Unbreakable', ('byte', 1))


def test_convert_components_display():
    """custom_name and lore -> display compound."""
    components = ('compound', [
        (8, 'minecraft:custom_name', ('string', '{"text":"My Sword"}')),
        (9, 'minecraft:lore', ('list', 8, [
            ('string', '{"text":"Line 1"}'),
            ('string', '{"text":"Line 2"}'),
        ])),
    ])
    result = _convert_components_to_tag(components)
    assert len(result) == 1
    tag_type, tag_name, tag_val = result[0]
    assert tag_type == 10
    assert tag_name == 'display'
    assert tag_val[0] == 'compound'
    inner = {n: v for _, n, v in tag_val[1]}
    assert inner['Name'] == ('string', '{"text":"My Sword"}')
    assert inner['Lore'][0] == 'list'
    assert len(inner['Lore'][2]) == 2


def test_convert_components_mixed():
    """Multiple components at once."""
    components = ('compound', [
        (10, 'minecraft:enchantments', ('compound', [
            (10, 'levels', ('compound', [
                (3, 'minecraft:sharpness', ('int', 5)),
            ])),
        ])),
        (3, 'minecraft:damage', ('int', 50)),
        (8, 'minecraft:custom_name', ('string', '{"text":"Test"}')),
        (3, 'minecraft:repair_cost', ('int', 3)),
    ])
    result = _convert_components_to_tag(components)
    names = {n for _, n, _ in result}
    assert 'Enchantments' in names
    assert 'Damage' in names
    assert 'RepairCost' in names
    assert 'display' in names


def test_convert_components_empty():
    components = ('compound', [])
    assert _convert_components_to_tag(components) == []


def test_convert_components_non_compound():
    assert _convert_components_to_tag(('string', 'invalid')) == []


def test_convert_item_with_components():
    """Full item conversion: count->Count, components->tag."""
    item_entries = [
        (8, 'id', ('string', 'minecraft:diamond_sword')),
        (3, 'count', ('int', 1)),
        (10, 'components', ('compound', [
            (10, 'minecraft:enchantments', ('compound', [
                (10, 'levels', ('compound', [
                    (3, 'minecraft:sharpness', ('int', 5)),
                    (3, 'minecraft:unbreaking', ('int', 3)),
                ])),
            ])),
            (3, 'minecraft:damage', ('int', 100)),
        ])),
    ]
    result = _convert_item(item_entries)
    result_map = {n: (t, v) for t, n, v in result}

    assert 'id' in result_map
    assert result_map['id'][1] == ('string', 'minecraft:diamond_sword')

    assert 'Count' in result_map
    assert result_map['Count'] == (1, ('byte', 1))

    assert 'components' not in result_map

    assert 'tag' in result_map
    tag_type, tag_val = result_map['tag']
    assert tag_type == 10
    assert tag_val[0] == 'compound'
    inner = {n: v for _, n, v in tag_val[1]}
    assert 'Enchantments' in inner
    assert 'Damage' in inner


def test_convert_item_without_components():
    """Item without components should work as before."""
    item_entries = [
        (8, 'id', ('string', 'minecraft:stone')),
        (3, 'count', ('int', 64)),
    ]
    result = _convert_item(item_entries)
    result_map = {n: (t, v) for t, n, v in result}
    assert 'Count' in result_map
    assert result_map['Count'] == (1, ('byte', 64))
    assert 'tag' not in result_map


def test_convert_item_slot_preserved():
    """Slot tag should pass through unchanged."""
    item_entries = [
        (8, 'id', ('string', 'minecraft:stone')),
        (3, 'count', ('int', 1)),
        (1, 'Slot', ('byte', 0)),
    ]
    result = _convert_item(item_entries)
    result_map = {n: (t, v) for t, n, v in result}
    assert 'Slot' in result_map
    assert result_map['Slot'] == (1, ('byte', 0))
