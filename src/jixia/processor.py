import logging
from typing import TypeVar
from pydantic import BaseModel
from .structs import RootModel, Declaration, Symbol, InfoTree, ModuleInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeclarationBundle(BaseModel):
    """
    A declaration pack contains a declaration, and its corresponding
    symbol and info tree.
    """
    declaration: Declaration
    symbol: Symbol
    info_tree: InfoTree
    module_info: ModuleInfo

class JixiaBundle(BaseModel):
    """
    A Jixia bundle is the direct results from jixia.
    """
    declarations: list[Declaration]
    symbols: list[Symbol]
    info_trees: list[InfoTree]
    module_info: ModuleInfo

M = TypeVar("M", bound="RootModel")

class JixiaProcessor:
    """
    This processor takes in a lean4 file and returns jixia
    structures
    """
    
    def __init__(self, root: str) -> None:
        """
        :param root: path to your lean test dir
        """
        self.root = root
    
    @staticmethod
    def sort_bundle(jixia_bundle: JixiaBundle) -> list[DeclarationBundle]:
        """
        For each declaration, identify its corresponding symbol and info tree.
        Symbols are identified by name, and info trees are identified by the string range.
        """
        declaration_bundles = []
        for decl in jixia_bundle.declarations:
            symbol = next((s for s in jixia_bundle.symbols if s.name == decl.name), None)
            info_tree = next((it for it in jixia_bundle.info_trees if it.ref.range == decl.ref.range), None)
            if symbol is None or info_tree is None:
                raise ValueError(f"Symbol or info tree not found for declaration {decl.name}")
            declaration_bundles.append(DeclarationBundle(
                declaration=decl,
                symbol=symbol,
                info_tree=info_tree,
                module_info=jixia_bundle.module_info,
            ))
        return declaration_bundles