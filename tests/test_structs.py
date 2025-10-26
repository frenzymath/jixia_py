from pathlib import Path

from jixia.structs import Declaration, InfoTree


def test_declaration():
    declarations = Declaration.from_json_file(Path(__file__).parent / "Example.decl.json")
    infotree = InfoTree.from_json_file(Path(__file__).parent / "Example.elab.json")
    print(declarations)
    print(infotree)
