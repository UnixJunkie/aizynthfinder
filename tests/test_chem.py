import pytest
from rdkit import Chem

from aizynthfinder.chem import (
    MoleculeException,
    Molecule,
    TreeMolecule,
    Reaction,
    RetroReaction,
)


def test_no_input():
    with pytest.raises(MoleculeException):
        Molecule()


def test_create_with_mol():
    rd_mol = Chem.MolFromSmiles("O")

    mol = Molecule(rd_mol=rd_mol)

    assert mol.smiles == "O"


def test_create_with_smiles():
    mol = Molecule(smiles="O")

    assert Chem.MolToSmiles(mol.rd_mol) == "O"


def test_inchi():
    mol = Molecule(smiles="O")

    assert mol.inchi == "InChI=1S/H2O/h1H2"


def test_inchi_key():
    mol = Molecule(smiles="O")

    assert mol.inchi_key == "XLYOFNOQVPJJNP-UHFFFAOYSA-N"


def test_fingerprint():
    mol = Molecule(smiles="O")

    assert sum(mol.fingerprint(2)) == 1

    assert sum(mol.fingerprint(2, 10)) == 1


def test_sanitize():
    mol = Molecule(smiles="O", sanitize=True)

    assert Chem.MolToSmiles(mol.rd_mol) == "O"

    mol = Molecule(smiles="c1ccccc1(C)(C)")

    with pytest.raises(MoleculeException):
        mol.sanitize()

    mol.sanitize(raise_exception=False)
    assert mol.smiles == "CC1(C)CCCCC1"


def test_equality():
    mol1 = Molecule(smiles="CCCCO")
    mol2 = Molecule(smiles="OCCCC")

    assert mol1 == mol2


def test_basic_equality():
    mol1 = Molecule(smiles="CC[C@@H](C)O")  # R-2-butanol
    mol2 = Molecule(smiles="CC[C@H](C)O")  # S-2-butanol

    assert mol1 != mol2
    assert mol1.basic_compare(mol2)


def test_has_atom_mapping():
    mol1 = Molecule(smiles="CCCCO")
    mol2 = Molecule(smiles="C[C:5]CCO")

    assert not mol1.has_atom_mapping()
    assert mol2.has_atom_mapping()


def test_remove_atom_mapping():
    mol = Molecule(smiles="C[C:5]CCO")

    assert mol.has_atom_mapping()

    mol.remove_atom_mapping()

    assert not mol.has_atom_mapping()


def test_retro_reaction(simple_actions):
    mol = TreeMolecule(parent=None, smiles="CCCCOc1ccc(CC(=O)N(C)O)cc1")
    reactions, _ = simple_actions(mol)

    products1 = reactions[0].apply()
    assert products1[0][0].smiles == "CCCCOc1ccc(CC(=O)Cl)cc1"
    assert products1[0][1].smiles == "CNO"

    products2 = reactions[2].apply()
    assert products2 == ()


def test_reaction_failure_rdchiral(simple_actions, mocker):
    patched_rchiral_run = mocker.patch("aizynthfinder.chem.rdc.rdchiralRun")
    patched_rchiral_run.side_effect = RuntimeError("Oh no!")
    mol = TreeMolecule(parent=None, smiles="CCCCOc1ccc(CC(=O)N(C)O)cc1")
    reactions, _ = simple_actions(mol)

    products = reactions[0].apply()
    assert not products


def test_fwd_reaction():
    mol1 = Molecule(smiles="CC(=O)O", sanitize=True)
    mol2 = Molecule(smiles="NC", sanitize=True)
    reaction = Reaction(
        mols=[mol1, mol2], smarts="[C:1](=[O:2])-[OD1].[N!H0:3]>>[C:1](=[O:2])[N:3]"
    )

    products = reaction.apply()

    assert len(products) == 1
    assert len(products[0]) == 1
    assert products[0][0].smiles == "CNC(C)=O"


def test_retro_reaction_fingerprint(simple_actions):
    mol = TreeMolecule(parent=None, smiles="CCCCOc1ccc(CC(=O)N(C)O)cc1")
    reactions, _ = simple_actions(mol)

    fp = reactions[0].fingerprint(2, 10)

    assert list(fp) == [0, -1, 0, -1, -1, 0, -1, -1, 0, 0]


def test_retro_reaction_copy(simple_actions):
    mol = TreeMolecule(parent=None, smiles="CCCCOc1ccc(CC(=O)N(C)O)cc1")
    reactions, _ = simple_actions(mol)
    reactions[0].apply()

    copy_ = reactions[0].copy()

    assert copy_.mol.smiles == reactions[0].mol.smiles
    assert len(copy_.reactants[0]) == len(reactions[0].reactants[0])
    assert copy_.index == reactions[0].index

    copy_ = reactions[0].copy(index=2)

    assert copy_.mol.smiles == reactions[0].mol.smiles
    assert len(copy_.reactants[0]) == len(reactions[0].reactants[0])
    assert copy_.index != reactions[0].index


def test_make_reaction_from_smiles():
    smiles = "CCCCOc1ccc(CC(=O)N(C)O)cc1>>CCCCOc1ccc(CC(=O)Cl)cc1.CNO"

    rxn = RetroReaction.from_reaction_smiles(smiles, smarts="")

    assert rxn.mol.smiles == "CCCCOc1ccc(CC(=O)N(C)O)cc1"
    assert len(rxn.reactants[0]) == 2
    assert rxn.reactants[0][0].smiles == "CCCCOc1ccc(CC(=O)Cl)cc1"
    assert rxn.reactants[0][1].smiles == "CNO"
