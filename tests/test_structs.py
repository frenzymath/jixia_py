from pathlib import Path

from jixia.structs import Declaration, InfoTree, Symbol


def test_declaration():
    declarations = Declaration.from_json_file(Path(__file__).parent / "Example.decl.json")
    symbols = Symbol.from_json_file(Path(__file__).parent / "Example.sym.json")
    infotree = InfoTree.from_json_file(Path(__file__).parent / "Example.elab.json")
    print(declarations)
    print(symbols)
    print(infotree)
