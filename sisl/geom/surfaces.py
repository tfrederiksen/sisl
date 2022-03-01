# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from collections import namedtuple
from numbers import Integral
import numpy as np

from sisl._internal import set_module
from sisl import Atom, Geometry, SuperCell

__all__ = ['fcc_slab', 'bcc_slab', 'rocksalt_slab']


def _layer2int(layer, periodicity):
    """Convert layer specification to integer"""
    if layer is None:
        return None
    if isinstance(layer, str):
        layer = "ABCDEF".index(layer.upper())
    return layer % periodicity


def _calc_info(start, end, layers, periodicity):
    """Determine offset index from start or end specification"""
    if start is not None and end is not None:
        raise ValueError("Only one of 'start' or 'end' may be supplied")

    Info = namedtuple("Info", ["layers", "nlayers", "offset", "periodicity"])

    # First check valid input, start or end should conform or die
    stacking = "ABCDEF"[:periodicity]

    # convert to integers in range range(periodicity)
    # However, if they are None, they will still be none
    start = _layer2int(start, periodicity)
    end = _layer2int(end, periodicity)

    # First convert `layers` to integer, and possibly determine start/end
    if layers is None:
        # default to a single stacking
        layers = periodicity

    if isinstance(layers, Integral):
        # convert to proper layers
        nlayers = layers

        # + 2 to allow rotating
        layers = stacking * (nlayers // periodicity + 2)

        if start is None and end is None:
            # the following will figure it out
            layers = layers[:nlayers]
        elif start is None:
            # end is not none
            layers = layers[end+1:] + layers[:end+1]
            layers = layers[-nlayers:]
        elif end is None:
            # start is not none
            layers = layers[start:] + layers[:start]
            layers = layers[:nlayers]

    elif isinstance(layers, str):
        nlayers = len(layers)

        try:
            # + 2 to allow rotating
            (stacking * (nlayers // periodicity + 2)).index(layers)
        except ValueError:
            raise NotImplementedError(f"Stacking faults are not implemented, requested {layers} with stacking {stacking}")

        if start is None and end is None:
            # easy case, we just calculate one of them
            start = _layer2int(layers[0], periodicity)

        elif start is not None:
            if _layer2int(layers[0], periodicity) != start:
                raise ValueError(f"Passing both 'layers' and 'start' requires them to be conforming; found layers={layers} "
                                 f"and start={'ABCDEF'[start]}")
        elif end is not None:
            if _layer2int(layers[-1], periodicity) != end:
                raise ValueError(f"Passing both 'layers' and 'end' requires them to be conforming; found layers={layers} "
                                 f"and end={'ABCDEF'[end]}")

    # a sanity check for the algorithm, should always hold!
    if start is not None:
        assert _layer2int(layers[0], periodicity) == start
    if end is not None:
        assert _layer2int(layers[-1], periodicity) == end

    # Convert layers variable to the list of layers in integer space
    layers = [_layer2int(l, periodicity) for l in layers]
    return Info(layers, nlayers, _layer2int(layers[0], periodicity), periodicity)


def _finish_slab(g, vacuum):
    """Grow slab according vacuum specifications"""
    d = np.ones(3) * 1e-4
    g = g.move(d).translate2uc().move(-d)
    g.xyz = np.where(g.xyz > 0, g.xyz, 0)
    g = g.sort(lattice=[2, 1, 0])
    if vacuum is not None:
        g.cell[2, 2] += vacuum
        g.set_nsc([3, 3, 1])
    else:
        g.set_nsc([3, 3, 3])
    if np.all(g.maxR(True) > 0.):
        g.optimize_nsc()
    return g


def _convert_miller(miller):
    """Convert miller specification to 3-tuple"""
    if isinstance(miller, int):
        miller = str(miller)
    if isinstance(miller, str):
        miller = [int(i) for i in miller]
    if isinstance(miller, list):
        miller = tuple(miller)
    if len(miller) != 3:
        raise ValueError(f"Invalid Miller indices, must have length 3")
    return miller


@set_module("sisl.geom")
def fcc_slab(alat, atoms, miller, layers=None, vacuum=20., *, orthogonal=False, start=None, end=None):
    r""" Construction of a surface slab from a face-centered cubic (FCC) crystal

    The slab layers are stacked along the :math:`z`-axis. The default stacking is the first
    layer as an A-layer, defined as the plane containing an atom at :math:`(x,y)=(0,0)`.

    Parameters
    ----------
    alat : float
        lattice constant of the fcc crystal
    atoms : Atom
        the atom that the crystal consists of
    miller : int or str or (3,)
        Miller indices of the surface facet
    layers : int or str, optional
        Number of layers in the slab or explicit layer specification.
        Currently the layers cannot have stacking faults.
    vacuum : float, optional
        distance added to the third lattice vector to separate
        the slab from its periodic images. If this is None, the slab will be a fully
        periodic geometry but with the slab layers. Useful for appending geometries together.
    orthogonal : bool, optional
        if True returns an orthogonal lattice
    start : int or string, optional
        sets the first layer in the slab. Only one of `start` or `end` must be specified.
        If set together with `layers` being a str, then they *must* be conforming.
    end : int or string, optional
        sets the last layer in the slab. Only one of `start` or `end` must be specified.
        If set together with `layers` being a str, then they *must* be conforming.

    Examples
    --------
    fcc 111 surface, starting with the A layer
    >>> fcc_slab(alat, atoms, "111", start=0)

    fcc 111 surface, starting with the B layer
    >>> fcc_slab(alat, atoms, "111", start=1)

    fcc 111 surface, ending with the B layer
    >>> fcc_slab(alat, atoms, "111", end='B')

    fcc 111 surface, with explicit layers in a given order
    >>> fcc_slab(alat, atoms, "111", layers='BCABCA')

    Raises
    ------
    NotImplementedError
        In case the Miller index has not been implemented or a stacking fault is
        introduced in `layers`.

    See Also
    --------
    fcc : Fully periodic equivalent of this slab structure
    bcc_slab : Slab in BCC structure
    rocksalt_slab : Slab in rocksalt/halite structure
    """
    miller = _convert_miller(miller)

    if miller == (1, 0, 0):

        info = _calc_info(start, end, layers, 2)

        sc = SuperCell(np.array([0.5 ** 0.5, 0.5 ** 0.5, 0.5]) * alat)
        g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
        g = g.tile(info.nlayers, 2)

        # slide AB layers relative to each other
        B = (info.offset + 1) % 2
        g.xyz[B::2] += (sc.cell[0] + sc.cell[1]) / 2

    elif miller == (1, 1, 0):

        info = _calc_info(start, end, layers, 2)

        sc = SuperCell(np.array([1., 0.5, 0.125]) ** 0.5 * alat)
        g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
        g = g.tile(info.nlayers, 2)

        # slide AB layers relative to each other
        B = (info.offset + 1) % 2
        g.xyz[B::2] += (sc.cell[0] + sc.cell[1]) / 2

    elif miller == (1, 1, 1):

        info = _calc_info(start, end, layers, 3)

        if orthogonal:
            sc = SuperCell(np.array([0.5, 4 * 0.375, 1 / 3]) ** 0.5 * alat)
            g = Geometry(np.array([[0, 0, 0],
                                   [0.125, 0.375, 0]]) ** 0.5 * alat,
                         atoms=atoms, sc=sc)
            g = g.tile(info.nlayers, 2)

            # slide ABC layers relative to each other
            B = 2 * (info.offset + 1) % 6
            C = 2 * (info.offset + 2) % 6
            vec = (3 * sc.cell[0] + sc.cell[1]) / 6
            g.xyz[B::6] += vec
            g.xyz[B+1::6] += vec
            g.xyz[C::6] += 2 * vec
            g.xyz[C+1::6] += 2 * vec

        else:
            sc = SuperCell(np.array([[0.5, 0, 0],
                                     [0.125, 0.375, 0],
                                     [0, 0, 1 / 3]]) ** 0.5 * alat)
            g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
            g = g.tile(info.nlayers, 2)

            # slide ABC layers relative to each other
            B = (info.offset + 1) % 3
            C = (info.offset + 2) % 3
            vec = (sc.cell[0] + sc.cell[1]) / 3
            g.xyz[B::3] += vec
            g.xyz[C::3] += 2 * vec

    else:
        raise NotImplementedError(f"fcc_slab: miller={miller} is not implemented")

    g = _finish_slab(g, vacuum)
    return g


def bcc_slab(alat, atoms, miller, layers=None, vacuum=20., *, orthogonal=False, start=None, end=None):
    r""" Construction of a surface slab from a body-centered cubic (BCC) crystal

    The slab layers are stacked along the :math:`z`-axis. The default stacking is the first
    layer as an A-layer, defined as the plane containing an atom at :math:`(x,y)=(0,0)`.

    Parameters
    ----------
    alat : float
        lattice constant of the fcc crystal
    atoms : Atom
        the atom that the crystal consists of
    miller : int or str or 3-array
        Miller indices of the surface facet
    layers : int or str, optional
        Number of layers in the slab or explicit layer specification.
        Currently the layers cannot have stacking faults.
    vacuum : float, optional
        distance added to the third lattice vector to separate
        the slab from its periodic images. If this is None, the slab will be a fully
        periodic geometry but with the slab layers. Useful for appending geometries together.
    orthogonal : bool, optional
        if True returns an orthogonal lattice
    start : int or string, optional
        sets the first layer in the slab. Only one of `start` or `end` must be specified.
        If set together with `layers` being a str, then they *must* be conforming.
    end : int or string, optional
        sets the last layer in the slab. Only one of `start` or `end` must be specified.
        If set together with `layers` being a str, then they *must* be conforming.

    Examples
    --------
    bcc 111 surface, starting with the A layer
    >>> bcc_slab(alat, atoms, "111", start=0)

    bcc 111 surface, starting with the B layer
    >>> bcc_slab(alat, atoms, "111", start=1)

    bcc 111 surface, ending with the B layer
    >>> bcc_slab(alat, atoms, "111", end='B')

    bcc 111 surface, with explicit layers in a given order
    >>> bcc_slab(alat, atoms, "111", layers='BCABCA')

    Raises
    ------
    NotImplementedError
        In case the Miller index has not been implemented or a stacking fault is
        introduced in `layers`.

    See Also
    --------
    bcc : Fully periodic equivalent of this slab structure
    fcc_slab : Slab in FCC structure
    rocksalt_slab : Slab in rocksalt/halite structure
    """
    miller = _convert_miller(miller)

    if miller == (1, 0, 0):

        info = _calc_info(start, end, layers, 2)

        sc = SuperCell(np.array([1, 1, 0.5]) * alat)
        g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
        g = g.tile(info.nlayers, 2)

        # slide AB layers relative to each other
        B = (info.offset + 1) % 2
        g.xyz[B::2] += (sc.cell[0] + sc.cell[1]) / 2

    elif miller == (1, 1, 0):

        info = _calc_info(start, end, layers, 2)

        if orthogonal:
            sc = SuperCell(np.array([1, 2, 0.5]) ** 0.5 * alat)
            g = Geometry(np.array([[0, 0, 0],
                                   [0.5, 0.5 ** 0.5, 0]]) * alat,
                         atoms=atoms, sc=sc)
            g = g.tile(info.nlayers, 2)

            # slide ABC layers relative to each other
            B = 2 * (info.offset + 1) % 4
            vec = sc.cell[1] / 2
            g.xyz[B::4] += vec
            g.xyz[B+1::4] += vec

        else:
            sc = SuperCell(np.array([[1, 0, 0],
                                     [0.5, 0.5 ** 0.5, 0],
                                     [0, 0, 0.5 ** 0.5]]) * alat)
            g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
            g = g.tile(info.nlayers, 2)

            # slide AB layers relative to each other
            B = (info.offset + 1) % 2
            g.xyz[B::2] += sc.cell[0] / 2

    elif miller == (1, 1, 1):

        info = _calc_info(start, end, layers, 3)

        if orthogonal:
            sc = SuperCell(np.array([2, 4 * 1.5, 1 / 12]) ** 0.5 * alat)
            g = Geometry(np.array([[0, 0, 0],
                                   [0.5, 1.5, 0]]) ** 0.5 * alat,
                         atoms=atoms, sc=sc)
            g = g.tile(info.nlayers, 2)

            # slide ABC layers relative to each other
            B = 2 * (info.offset + 1) % 6
            C = 2 * (info.offset + 2) % 6
            vec = (sc.cell[0] + sc.cell[1]) / 3
            for i in range(2):
                g.xyz[B+i::6] += vec
                g.xyz[C+i::6] += 2 * vec

        else:
            sc = SuperCell(np.array([[2, 0, 0],
                                     [0.5, 1.5, 0],
                                     [0, 0, 1 / 12]]) ** 0.5 * alat)
            g = Geometry([0, 0, 0], atoms=atoms, sc=sc)
            g = g.tile(info.nlayers, 2)

            # slide ABC layers relative to each other
            B = (info.offset + 1) % 3
            C = (info.offset + 2) % 3
            vec = (sc.cell[0] + sc.cell[1]) / 3
            g.xyz[B::3] += vec
            g.xyz[C::3] += 2 * vec

    else:
        raise NotImplementedError(f"bcc_slab: miller={miller} is not implemented")

    g = _finish_slab(g, vacuum)
    return g


def rocksalt_slab(alat, atoms, miller, layers=None, vacuum=20., *, orthogonal=False, start=None, end=None):
    r""" Construction of a surface slab from a two-element rock-salt crystal

    This structure is formed by two interlocked fcc crystals for each of the two elements.

    The slab layers are stacked along the :math:`z`-axis. The default stacking is the first
    layer as an A-layer, defined as the plane containing the first atom in the atoms list
    at :math:`(x,y)=(0,0)`.

    Parameters
    ----------
    alat : float
        lattice constant of the rock-salt crystal
    atoms : list
        a list of two atoms that the crystal consist of
    miller : int or str or 3-array
        Miller indices of the surface facet
    layers : int or str, optional
        Number of layers in the slab or explicit layer specification.
        Currently the layers cannot have stacking faults.
    vacuum : float, optional
        distance added to the third lattice vector to separate
        the slab from its periodic images. If this is None, the slab will be a fully
        periodic geometry but with the slab layers. Useful for appending geometries together.
    orthogonal : bool, optional
        if True returns an orthogonal lattice
    start : int or string, optional
        sets the first layer in the slab. Only one of `start` or `end` must be specified.
        If set together with `layers` being a str, then they *must* be conforming.
    end : int or string, optional
        sets the last layer in the slab. Only one of `start` or `end` must be specified.
        If set together with `layers` being a str, then they *must* be conforming.

    Examples
    --------
    NaCl(100) slab, starting with A-layer
    >>> rocksalt_slab(5.64, ['Na', 'Cl'], 100)

    6-layer NaCl(100) slab, ending with A-layer
    >>> rocksalt_slab(5.64, ['Na', 'Cl'], 100, layers=6, end='A')

    6-layer NaCl(100) slab, ending with A-layer
    >>> rocksalt_slab(5.64, ['Na', 'Cl'], 100, layers=6, end='A')

    Raises
    ------
    NotImplementedError
        In case the Miller index has not been implemented or a stacking fault is
        introduced in `layers`.

    See Also
    --------
    fcc_slab : Slab in FCC structure (this slab is a combination of fcc slab structures)
    bcc_slab : Slab in BCC structure
    """
    if len(atoms) != 2:
        raise ValueError(f"Invalid list of atoms, must have length 2")
    if isinstance(atoms, str):
        atoms = [atoms, atoms]

    miller = _convert_miller(miller)

    g1 = fcc_slab(alat, atoms[0], miller, layers=layers, vacuum=None, orthogonal=orthogonal, start=start, end=end)
    g2 = fcc_slab(alat, atoms[1], miller, layers=layers, vacuum=None, orthogonal=orthogonal, start=start, end=end)

    if miller == (1, 0, 0):
        g2 = g2.move(np.array([0.5, 0.5, 0]) ** 0.5 * alat / 2)

    elif miller == (1, 1, 0):
        g2 = g2.move(np.array([1, 0, 0]) * alat / 2)

    elif miller == (1, 1, 1):
        g2 = g2.move(np.array([0, 2 / 3, 1 / 3]) ** 0.5 * alat / 2)

    else:
        raise NotImplementedError(f"rocksalt_slab: miller={miller} is not implemented")

    g = g1.add(g2)

    g = _finish_slab(g, vacuum)
    return g
