# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import pytest

from sisl import Atom
from sisl.geom import *

import math as m
import numpy as np


pytestmark = [pytest.mark.geom]


def test_basis():
    a = sc(2.52, Atom['Fe'])
    a = bcc(2.52, Atom['Fe'])
    a = bcc(2.52, Atom['Fe'], orthogonal=True)
    a = fcc(2.52, Atom['Au'])
    a = fcc(2.52, Atom['Au'], orthogonal=True)
    a = hcp(2.52, Atom['Au'])
    a = hcp(2.52, Atom['Au'], orthogonal=True)


def test_flat():
    a = graphene()
    a = graphene(atoms='C')
    a = graphene(orthogonal=True)


def test_nanotube():
    a = nanotube(1.42)
    a = nanotube(1.42, chirality=(3, 5))
    a = nanotube(1.42, chirality=(6, -3))


def test_diamond():
    a = diamond()


def test_bilayer():
    a = bilayer(1.42)
    a = bilayer(1.42, stacking='AA')
    a = bilayer(1.42, stacking='BA')
    a = bilayer(1.42, stacking='AB')
    for m in range(7):
        a = bilayer(1.42, twist=(m, m + 1))
    a = bilayer(1.42, twist=(6, 7), layer='bottom')
    a = bilayer(1.42, twist=(6, 7), layer='TOP')
    a = bilayer(1.42, bottom_atoms=(Atom['B'], Atom['N']), twist=(6, 7))
    a = bilayer(1.42, top_atoms=(Atom(5), Atom(7)), twist=(6, 7))
    a, th = bilayer(1.42, twist=(6, 7), ret_angle=True)

    with pytest.raises(ValueError):
        bilayer(1.42, twist=(6, 7), layer='undefined')

    with pytest.raises(ValueError):
        bilayer(1.42, twist=(6, 7), stacking='undefined')

    with pytest.raises(ValueError):
        bilayer(1.42, twist=('str', 7), stacking='undefined')


def test_nanoribbon():
    for w in range(0, 5):
        a = nanoribbon(w, 1.42, Atom(6), kind='armchair')
        a = nanoribbon(w, 1.42, Atom(6), kind='zigzag')
        a = nanoribbon(w, 1.42, (Atom(5), Atom(7)), kind='armchair')
        a = nanoribbon(w, 1.42, (Atom(5), Atom(7)), kind='zigzag')

    with pytest.raises(ValueError):
        nanoribbon(6, 1.42, (Atom(5), Atom(7)), kind='undefined')

    with pytest.raises(ValueError):
        nanoribbon('str', 1.42, (Atom(5), Atom(7)), kind='undefined')


def test_graphene_nanoribbon():
    a = graphene_nanoribbon(5)


def test_agnr():
    a = agnr(5)


def test_zgnr():
    a = zgnr(5)


def test_fcc_slab():
    for o in [True, False]:
        g = fcc_slab(alat=4.08, atoms='Au', miller=(1, 0, 0), orthogonal=o)
        g = fcc_slab(4.08, 'Au', 100, orthogonal=o)
        g = fcc_slab(4.08, 'Au', 110, orthogonal=o)
        g = fcc_slab(4.08, 'Au', 111, orthogonal=o)
        g = fcc_slab(4.08, 79, '100', layers=5, rep=(3, 4), orthogonal=o)
        g = fcc_slab(4.08, 79, '110', layers=5, rep=(3, 4), vacuum=10, orthogonal=o)
        g = fcc_slab(4.08, 79, '111', layers=5, rep=(3, 4), start=1, orthogonal=o)
        g = fcc_slab(4.08, 79, '111', layers=5, rep=(3, 4), start='C', orthogonal=o)
        g = fcc_slab(4.08, 79, '111', layers=5, rep=(3, 4), end=2, orthogonal=o)
        g = fcc_slab(4.08, 79, '111', layers=5, rep=(3, 4), end='B', orthogonal=o)
    with pytest.raises(ValueError):
        fcc_slab(4.08, 'Au', 100, start=0, end=0)
        fcc_slab(4.08, 'Au', 1000)
    with pytest.raises(NotImplementedError):
        fcc_slab(4.08, 'Au', 200)


def test_bcc_slab():
    for o in [True, False]:
        g = bcc_slab(alat=4.08, atoms='Au', miller=(1, 0, 0), orthogonal=o)
        g = bcc_slab(4.08, 'Au', 100, orthogonal=o)
        g = bcc_slab(4.08, 'Au', 110, orthogonal=o)
        g = bcc_slab(4.08, 'Au', 111, orthogonal=o)
        g = bcc_slab(4.08, 79, '100', layers=5, rep=(3, 4), orthogonal=o)
        g = bcc_slab(4.08, 79, '110', layers=5, rep=(3, 4), vacuum=10, orthogonal=o)
        g = bcc_slab(4.08, 79, '111', layers=5, rep=(3, 4), start=1, orthogonal=o)
        g = bcc_slab(4.08, 79, '111', layers=5, rep=(3, 4), start='C', orthogonal=o)
        g = bcc_slab(4.08, 79, '111', layers=5, rep=(3, 4), end=2, orthogonal=o)
        g = bcc_slab(4.08, 79, '111', layers=5, rep=(3, 4), end='B', orthogonal=o)
    with pytest.raises(ValueError):
        bcc_slab(4.08, 'Au', 100, start=0, end=0)
        bcc_slab(4.08, 'Au', 1000)
    with pytest.raises(NotImplementedError):
        bcc_slab(4.08, 'Au', 200)

def test_rocksalt_slab():
    g = rocksalt_slab(5.64, [Atom(11, R=3), Atom(17, R=4)], 100)
    g = rocksalt_slab(5.64, ['Na', 'Cl'], 100, layers=5, rep=(3, 4))
    g = rocksalt_slab(5.64, ['Na', 'Cl'], 110)
    g = rocksalt_slab(5.64, ['Na', 'Cl'], 111, orthogonal=False)
    g = rocksalt_slab(5.64, ['Na', 'Cl'], 111, orthogonal=True)
    with pytest.raises(ValueError):
        rocksalt_slab(5.64, 'Na', 100)
        rocksalt_slab(5.64, ['Na', 'Cl'], 100, start=0, end=0)
        rocksalt_slab(5.64, ['Na', 'Cl'], 1000)
    with pytest.raises(NotImplementedError):
        rocksalt_slab(5.64, ['Na', 'Cl'], 200)
