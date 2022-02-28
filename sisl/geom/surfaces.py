# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import numpy as np

from sisl._internal import set_module
from sisl import Atom, Geometry, SuperCell

__all__ = ['fcc_slab', 'bcc_slab']


def _layer2int(layer):
    "Convert layer specification to integer"
    if isinstance(layer, str):
        layer = "ABCDEF".index(layer.upper())
    return layer


def _calc_offset(start, end, layers):
    "Determine offset index from start or end specification"
    if start is not None:
        return -_layer2int(start)
    return layers - 1 - _layer2int(end)


def _finish_slab(g, size, vacuum):
    "Grow slab according to size and vacuum specifications"
    g = g.repeat(size[1], 1).repeat(size[0], 0)
    if vacuum is not None:
        g.cell[2, 2] += vacuum
        g.set_nsc([3, 3, 1])
    else:
        g.set_nsc([3, 3, 3])
    if np.all(g.maxR(True) > 0.):
        g.optimize_nsc()
    return g


def _convert_miller(miller):
    "Convert miller specification to 3-tuple"
    if isinstance(miller, int):
        miller = str(miller)
    if isinstance(miller, str):
        miller = (int(miller[0]), int(miller[1]), int(miller[2]))
    if len(miller) != 3:
        raise ValueError(f"Invalid Miller indices")
    return miller


@set_module("sisl.geom")
def fcc_slab(alat, atoms, miller, size=None, vacuum=None, orthogonal=False, start=None, end=None):
    """ Construction of a surface slab from a face-centered cubic (FCC) crystal

    The slab layers are stacked along the z-axis. The default stacking is the first
    layer as an A-layer, defined as the plane containing an atom at (x,y)=(0,0).

    Parameters
    ----------
    alat : float
        lattice constant of the fcc crystal
    atoms : Atom
        the atom that the crystal consists of
    miller : int or str or (3,)
        Miller indices of the surface facet
    size : 3-array, optional
        slab size along the lattice vectors
    vacuum : float, optional
        distance added to the third lattice vector to separate
        the slab from its periodic images
    orthogonal : bool, optional
        if True returns an orthogonal lattice
    start : int or string, optional
        sets the first layer in the slab. Only one of `start` or `end` must be specified.
    end : int or string, optional
        sets the last layer in the slab. Only one of `start` or `end` must be specified.

    Examples
    --------
    fcc 111 surface, starting with the A layer

    >>> fcc_slab(alat, atoms, "111", start=0)

    fcc 111 surface, starting with the B layer
    >>> fcc_slab(alat, atoms, "111", start=1)

    fcc 111 surface, ending with the B layer
    >>> fcc_slab(alat, atoms, "111", end=1)

    See Also
    --------
    geom.fcc
    geom.bcc_slab
    """
    miller = _convert_miller(miller)

    if start is not None and end is not None:
        raise ValueError("fcc_slab: Only one of 'start' or 'end' may be supplied")

    if start is None and end is None:
        start = 0

    if miller == (1, 0, 0):

        if size is None:
            size = (1, 1, 2)

        sc = SuperCell(np.array([0.5 ** 0.5, 0.5 ** 0.5, 0.5]) * alat)
        g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
        g = g.tile(size[2], 2)

        # slide AB layers relative to each other
        offset = _calc_offset(start, end, size[2])
        B = (offset + 1) % 2
        g.xyz[B::2] += (sc.cell[0] + sc.cell[1]) / 2

    elif miller == (1, 1, 0):

        if size is None:
            size = (1, 1, 2)

        sc = SuperCell(np.array([1., 0.5, 0.125]) ** 0.5 * alat)
        g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
        g = g.tile(size[2], 2)

        # slide AB layers relative to each other
        offset = _calc_offset(start, end, size[2])
        B = (offset + 1) % 2
        g.xyz[B::2] += (sc.cell[0] + sc.cell[1]) / 2

    elif miller == (1, 1, 1):

        if size is None:
            size = (1, 1, 3)

        if orthogonal:
            sc = SuperCell(np.array([0.5, 4 * 0.375, 1 / 3]) ** 0.5 * alat)
            g = Geometry(np.array([[0, 0, 0],
                                   [0.125, 0.375, 0]]) ** 0.5 * alat,
                         atoms=atoms, sc=sc)
            g = g.tile(size[2], 2)

            # slide ABC layers relative to each other
            offset = _calc_offset(start, end, size[2])
            B = 2 * (offset + 1) % 6
            C = 2 * (offset + 2) % 6
            vec = 1.5 * sc.cell[0] + sc.cell[1] / 2
            g.xyz[B::6] += vec / 3
            g.xyz[C::6] += 2 * vec / 3 - sc.cell[0]
            g.xyz[B+1::6] += vec / 3 - sc.cell[0]
            g.xyz[C+1::6] += 2 * vec / 3 - sc.cell[0]

        else:
            sc = SuperCell(np.array([[0.5, 0, 0],
                                     [0.125, 0.375, 0],
                                     [0, 0, 1 / 3]]) ** 0.5 * alat)
            g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
            g = g.tile(size[2], 2)

            # slide ABC layers relative to each other
            offset = _calc_offset(start, end, size[2])
            B = (offset + 1) % 3
            C = (offset + 2) % 3
            g.xyz[B::3] += sc.cell[0] / 3 + sc.cell[1] / 3
            g.xyz[C::3] += -sc.cell[0] / 3 + 2 * sc.cell[1] / 3


    else:
         raise NotImplementedError(f"fcc_slab: miller={miller} is not implemented")

    g = _finish_slab(g, size, vacuum)
    return g


def bcc_slab(alat, atoms, miller, size=None, vacuum=None, orthogonal=False, start=None, end=None):
    """ Construction of a surface slab from a body-centered cubic (BCC) crystal

    The slab layers are stacked along the z-axis. The default stacking is the first
    layer as an A-layer, defined as the plane containing an atom at (x,y)=(0,0).

    Parameters
    ----------
    alat : float
        lattice constant of the fcc crystal
    atoms : Atom
        the atom that the crystal consists of
    miller : int or str or 3-array
        Miller indices of the surface facet
    size : 3-array, optional
        slab size along the lattice vectors
    vacuum : float, optional
        distance added to the third lattice vector to separate
        the slab from its periodic images
    orthogonal : bool, optional
        if True returns an orthogonal lattice
    start : int or string, optional
        sets the first layer in the slab
    end : int or string, optional
        sets the last layer in the slab

    See Also
    --------
    geom.bcc
    geom.fcc_slab
    """
    miller = _convert_miller(miller)

    if start is not None and end is not None:
        raise ValueError("Only one of start or end may be supplied")

    if start is None and end is None:
        start = 0

    if miller == (1, 0, 0):

        if size is None:
            size = (1, 1, 2)

        sc = SuperCell(np.array([1, 1, 0.5]) * alat)
        g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
        g = g.tile(size[2], 2)

        # slide AB layers relative to each other
        offset = _calc_offset(start, end, size[2])
        B = (offset + 1) % 2
        g.xyz[B::2] += (sc.cell[0] + sc.cell[1]) / 2

    elif miller == (1, 1, 0):

        if size is None:
            size = (1, 1, 2)

        if not orthogonal:
            sc = SuperCell(np.array([[1, 0, 0],
                                     [0.5, 0.5 ** 0.5, 0],
                                     [0, 0, 0.5 ** 0.5]]) * alat)
            g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
            g = g.tile(size[2], 2)

            # slide AB layers relative to each other
            offset = _calc_offset(start, end, size[2])
            B = (offset + 1) % 2
            g.xyz[B::2] += sc.cell[0] / 2

        elif orthogonal:
            sc = SuperCell(np.array([1, 2, 0.5]) ** 0.5 * alat)
            g = Geometry(np.array([[0, 0, 0],
                                   [0.5, 0.5 ** 0.5, 0]]) * alat,
                         atoms=atoms, sc=sc)
            g = g.tile(size[2], 2)

            # slide ABC layers relative to each other
            offset = _calc_offset(start, end, size[2])
            B = 2 * (offset + 1) % 4
            g.xyz[B::4] += sc.cell[1] / 2
            g.xyz[B+1::4] -= sc.cell[1] / 2

    elif miller == (1, 1, 1):

        if size is None:
            size = (1, 1, 3)

        if not orthogonal:
            sc = SuperCell(np.array([[2, 0, 0],
                                     [0.5, 1.5, 0],
                                     [0, 0, 1 / 12]]) ** 0.5 * alat)
            g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
            g = g.tile(size[2], 2)

            # slide ABC layers relative to each other
            offset = _calc_offset(start, end, size[2])
            B = (offset + 1) % 3
            C = (offset + 2) % 3
            g.xyz[B::3] += sc.cell[0] / 3 + sc.cell[1] / 3
            g.xyz[C::3] += -sc.cell[0] / 3 + 2 * sc.cell[1] / 3

        elif orthogonal:
            sc = SuperCell(np.array([2, 4 * 1.5, 1 / 12]) ** 0.5 * alat)
            g = Geometry(np.array([[0, 0, 0],
                                   [0.5, 1.5, 0]]) ** 0.5 * alat,
                         atoms=atoms, sc=sc)
            g = g.tile(size[2], 2)

            # slide ABC layers relative to each other
            offset = _calc_offset(start, end, size[2])
            B = 2 * (offset + 1) % 6
            C = 2 * (offset + 2) % 6
            vec = 1.5 * sc.cell[0] + sc.cell[1] / 2
            for i in range(2):
                g.xyz[B+i::6] += vec / 3 - i % 2 * sc.cell[0]
                g.xyz[C+i::6] += 2 * vec / 3 - sc.cell[0]

    else:
         raise NotImplementedError(f"miller={miller} is not implemented")

    g = _finish_slab(g, size, vacuum)
    return g
