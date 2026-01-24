# tags/registry.py

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple
import struct

# ---------------- Tag Definition ----------------

@dataclass(frozen=True)
class TagDef:
    name: str
    object_id: int
    cmd_id: int
    parser: Callable[[bytes], float]
    write_cmd: int | None = None
    writer: Callable[[any], bytes] | None = None


# ---------------- Helpers ----------------

def f32_at(offset: int):
    """Return parser that extracts float32 at offset"""
    return lambda payload: struct.unpack_from("<f", payload, offset)[0]


def u8_at(offset: int):
    """Return parser that extracts uint8 at offset"""
    return lambda payload: payload[offset]

def u8_writer(v):
    return struct.pack("<B", int(v))

def f32_writer(v):
    return struct.pack("<f", float(v))

# ---------------- Object IDs ----------------

OBJ_TIC1 = 1

# ---------------- Command IDs ----------------

CMD_READ_STATUS = 0x01

# ---------------- TempCtrl READ_STATUS layout ----------------
# struct:
# uint8  Mode
# uint8  CtrlMode
# uint16 pad
# float  Sp
# pide_stat_t follows

OFFSET_TC_MODE     = 0
OFFSET_TC_CTRLMODE = 1
OFFSET_TC_SP       = 4

OFFSET_PID_SP   = 8
OFFSET_PID_PV   = 12
OFFSET_PID_CV   = 16
OFFSET_PID_KP   = 20
OFFSET_PID_KI   = 24
OFFSET_PID_KD   = 28
OFFSET_PID_ERR  = 40
OFFSET_PID_MODE = 44

TC_CMD_SET_MODE = 0x20
TC_CMD_SET_SP   = 0x21


# ---------------- Registry ----------------

TAGS: Dict[str, TagDef] = {

    # --- TempCtrl ---
    "tic1.tc.mode": TagDef(
        name="tic1.tc.mode",
        object_id=OBJ_TIC1,
        cmd_id=CMD_READ_STATUS,
        parser=u8_at(OFFSET_TC_MODE),
        write_cmd=TC_CMD_SET_MODE,
        writer=u8_writer,
        ),

    "tic1.tc.ctrlmode": TagDef(
        "tic1.tc.ctrlmode", OBJ_TIC1, CMD_READ_STATUS, u8_at(OFFSET_TC_CTRLMODE)
    ),

    "tic1.sp": TagDef(
        name="tic1.sp",
        object_id=OBJ_TIC1,
        cmd_id=CMD_READ_STATUS,
        parser=f32_at(OFFSET_TC_SP),
        write_cmd=TC_CMD_SET_SP,
        writer=f32_writer,
        ),

    # --- PID ---
    "tic1.pid.sp": TagDef(
        "tic1.pid.sp", OBJ_TIC1, CMD_READ_STATUS, f32_at(OFFSET_PID_SP)
    ),

    "tic1.pid.pv": TagDef(
        "tic1.pid.pv", OBJ_TIC1, CMD_READ_STATUS, f32_at(OFFSET_PID_PV)
    ),

    "tic1.pid.cv": TagDef(
        "tic1.pid.cv", OBJ_TIC1, CMD_READ_STATUS, f32_at(OFFSET_PID_CV)
    ),

    "tic1.pid.kp": TagDef(
        "tic1.pid.kp", OBJ_TIC1, CMD_READ_STATUS, f32_at(OFFSET_PID_KP)
    ),

    "tic1.pid.ki": TagDef(
        "tic1.pid.ki", OBJ_TIC1, CMD_READ_STATUS, f32_at(OFFSET_PID_KI)
    ),

    "tic1.pid.kd": TagDef(
        "tic1.pid.kd", OBJ_TIC1, CMD_READ_STATUS, f32_at(OFFSET_PID_KD)
    ),

    "tic1.pid.err": TagDef(
        "tic1.pid.err", OBJ_TIC1, CMD_READ_STATUS, f32_at(OFFSET_PID_ERR)
    ),

    "tic1.pid.mode": TagDef(
        "tic1.pid.mode", OBJ_TIC1, CMD_READ_STATUS, u8_at(OFFSET_PID_MODE)
    ),
}


# ---------------- Lookup Utilities ----------------

def get_tag(name: str) -> TagDef:
    return TAGS[name]


def group_tags_by_command(tag_names: List[str]) -> Dict[Tuple[int, int], List[TagDef]]:
    """
    Returns:
      {(object_id, cmd_id): [TagDef, TagDef, ...]}
    """
    groups: Dict[Tuple[int, int], List[TagDef]] = {}

    for name in tag_names:
        tag = TAGS.get(name)
        if not tag:
            continue

        key = (tag.object_id, tag.cmd_id)
        groups.setdefault(key, []).append(tag)

    return groups
