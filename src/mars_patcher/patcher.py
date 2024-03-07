import json
from typing import Callable

from jsonschema import validate

from mars_patcher.connections import Connections
from mars_patcher.data import get_data_path
from mars_patcher.hints import Hints
from mars_patcher.item_patcher import ItemPatcher, set_metroid_count, set_tank_increments
from mars_patcher.locations import LocationSettings
from mars_patcher.random_palettes import PaletteRandomizer, PaletteSettings
from mars_patcher.rom import Rom
from mars_patcher.text import write_seed_hash
from mars_patcher.starting import set_starting_location, set_starting_items


def patch(input_path: str,
          output_path: str,
          patch_data_path: str,
          status_update: Callable[[float, str], None]
          ) -> None:
    # load input rom
    rom = Rom(input_path)

    # load patch data file and validate
    with open(patch_data_path) as f:
        patch_data = json.load(f)

    with open(get_data_path("schema.json")) as f:
        schema = json.load(f)
    validate(patch_data, schema)

    # randomize palettes - palettes are randomized first in case the item
    # patcher needs to copy tilesets
    if "Palettes" in patch_data:
        status_update(-1, "Randomizing palettes...")
        pal_settings = PaletteSettings.from_json(patch_data["Palettes"])
        pal_randomizer = PaletteRandomizer(rom, pal_settings)
        pal_randomizer.randomize()

    # load locations and set assignments
    status_update(-1, "Writing item assignments...")
    loc_settings = LocationSettings.initialize()
    loc_settings.set_assignments(patch_data["Locations"])
    item_patcher = ItemPatcher(rom, loc_settings)
    item_patcher.write_items()

    # required metroid count
    set_metroid_count(rom, patch_data["RequiredMetroidCount"])

    # starting location
    if "StartingLocation" in patch_data:
        status_update(-1, "Writing starting location...")
        set_starting_location(rom, patch_data["StartingLocation"])

    # starting items
    if "StartingItems" in patch_data:
        status_update(-1, "Writing starting items...")
        set_starting_items(rom, patch_data["StartingItems"])

    # tank increments
    if "TankIncrements" in patch_data:
        status_update(-1, "Writing tank increments...")
        set_tank_increments(rom, patch_data["TankIncrements"])

    # elevator connections
    if "ElevatorConnections" in patch_data:
        status_update(-1, "Writing elevator connections...")
        conns = Connections(rom)
        conns.set_elevator_connections(patch_data["ElevatorConnections"])

    # hints
    if "Hints" in patch_data:
        status_update(-1, "Writing hints...")
        hints = Hints.from_json(patch_data["Hints"])
        hints.write(rom)

    if patch_data.get("SkipDoorTransitions"):
        # TODO: move to separate patch
        rom.write_32(0x69500, 0x3000BDE)
        rom.write_8(0x694E2, 0xC)

    write_seed_hash(rom, patch_data["SeedHash"])

    rom.save(output_path)
    status_update(-1, f"Output written to {output_path}")
