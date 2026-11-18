from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class UserError(Exception):
    pass


class TreeMap(dict):
    @classmethod
    def __class_getitem__(cls, item):
        return cls


def load_contract(filename, class_name, fetch, sender):
    module = ModuleType("genlayer")
    module.TreeMap = TreeMap
    module.u32 = int
    module.i32 = int
    module.allow_storage = lambda cls: cls
    module.gl = SimpleNamespace(
        Contract=object,
        message=sender,
        public=SimpleNamespace(view=lambda fn: fn, write=lambda fn: fn),
        vm=SimpleNamespace(UserError=UserError),
        nondet=SimpleNamespace(web=SimpleNamespace(get=fetch)),
        eq_principle=SimpleNamespace(strict_eq=lambda run: run()),
    )
    source = Path(__file__).resolve().parents[1] / "contracts" / filename
    with patch.dict(sys.modules, {"genlayer": module}):
        cls = runpy.run_path(str(source))[class_name]
    instance = cls()
    for storage in cls.__annotations__:
        setattr(instance, storage, TreeMap())
    return instance
