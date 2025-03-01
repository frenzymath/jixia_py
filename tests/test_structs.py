from pathlib import Path

from jixia.structs import Declaration


def test_declaration():
    declarations = Declaration.from_json_file(Path(__file__).parent / "Example.decl.json")
    print(declarations)
