from .structs import InfoTree, StringRange, LeanName


def collect_reference(tree: InfoTree) -> list[tuple[StringRange, LeanName]]:
    if tree.ref.range is None:
        return []
    elab_info = tree.info
    if elab_info.term is not None \
            and elab_info.term.special is not None \
            and elab_info.term.special.const is not None:
        reference = [(tree.ref.range, elab_info.term.special.const)]
    else:
        reference = []
    for subtree in tree.children:
        reference += collect_reference(subtree)
    return reference
