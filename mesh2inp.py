# file: mesh2inp.py
# vim:fileencoding=utf-8:fdm=marker:ft=python
#
# Copyright © 2019 R.F. Smith <rsmith@xs4all.nl>
# SPDX-License-Identifier: MIT
# Created: 2019-03-10T17:41:26+0100
# Last modified: 2019-03-24T23:07:56+0100
"""Convert a mesh file to Calculix/Abaqus input data.

Requires three filenames:
* input mesh (.mesh)
* nodes and node sets file name (.inp)
* elements file name (.inp)
"""
from collections import defaultdict
import logging
import sys


def read_mesh(name):
    """Read a mesh file. Extract nodes, node sets and elements."""
    with open(name) as mesh:
        lines = [ln.strip() for ln in mesh.readlines()]
    # Remove comments, just in case
    lines = [ln for ln in lines if not ln.startswith('#')]
    # Get the points
    pi = lines.index('points') + 2
    numpoints = int(lines[pi-1])
    points = [tuple(float(j) for j in ln.split()) for ln in lines[pi:pi+numpoints]]
    # Get the surface elements
    si = lines.index('surfaceelements') + 2
    numelements = int(lines[si-1])
    elements = [tuple(int(j) for j in ln.split()) for ln in lines[si:si+numelements]]
    # Get the materials (node sets).
    mi = lines.index('materials') + 2
    nummaterials = int(lines[mi-1])
    materials = [ln.split() for ln in lines[mi:mi+nummaterials]]
    # Assuming the material name doesn't contain spaces.
    materials = [(int(m[0]), m[1]) for m in materials]
    # Get the edge boundaries. Surface ID's >100 are boundaries.
    edgeboundaries = []
    ei = lines.index('edgesegmentsgi2') + 2
    numedges = int(lines[ei-1])
    edges = [ln.split() for ln in lines[ei:ei+numedges]]
    edgeboundaries = defaultdict(set)
    for e in edges:
        key = int(e[0])
        if key > 100:
            edgeboundaries[key].add(int(e[2]))
            edgeboundaries[key].add(int(e[3]))
    return points, elements, materials, edgeboundaries


def chunks(sequence, count):
    """Split an sequence into chunks of count items."""
    if count < 1:
        raise ValueError('count must be > 0')
    for i in range(0, len(sequence), count):
        yield sequence[i:i+count]


def write_nodes(name, points, elements, materials, edge_boundaries):
    """Write the nodes and node sets file."""
    if not name.endswith('.inp'):
        name += '.inp'
    with open(name, 'wt') as nodefile:
        nodefile.write('**\n')
        nodefile.write(f'** {name}\n')
        nodefile.write('** Gegenereerd door mesh2inp.py.\n')
        nodefile.write('**\n')
        nodefile.write('*NODE,NSET=Nall\n')
        for n, (x, y, z) in enumerate(points, start=1):
            nodefile.write(f'{n}, {x:.2f}, {y:.2f}, {z:.2f}\n')
        for m in materials:
            matnum, matname = m
            nset = set()
            for e in [el for el in elements if el[1] == matnum]:
                nset.update(set(e[5:5+e[4]]))
            nodefile.write(f'*NSET,NSET=N{matname}\n')
            for sub in chunks(sorted(list(nset)), 16):
                nodefile.write('  '+', '.join(str(i) for i in sub)+'\n')
            logging.info(f'wrote {len(nset)} nodes to set N{matname}')
        for k in edge_boundaries.keys():
            nodes = sorted(list(edge_boundaries[k]))
            nodefile.write(f'*NSET,NSET=Nedge{k}\n')
            for sub in chunks(nodes, 16):
                nodefile.write('  '+', '.join(str(i) for i in sub)+'\n')
            logging.info(f'wrote {len(nodes)} nodes to set Nedge{k}')


def write_elements(name, elements, materials):
    """Write the elements file. This uses S6 shell elements.
    The ccw node sequence should be 1, 4, 2, 5, 3, 6.
    """
    with open(name, 'wt') as efile:
        efile.write('**\n')
        efile.write(f'** {name}\n')
        efile.write('** Gegenereerd door mesh2inp.py.\n')
        efile.write('**\n')
        efile.write('*ELEMENT, TYPE=S6, ELSET=Eall\n')
        for n, e in enumerate(elements, start=1):
            cnt = e[4]
            nodes = list(e[5:5+cnt])
            if cnt == 6:  # S6 element
                nodes = [
                    n, nodes[0], nodes[1], nodes[2], nodes[5], nodes[3], nodes[4]
                ]
                efile.write(', '.join(str(j) for j in nodes)+'\n')
        for m in materials:
            matnum, matname = m
            efile.write(f'*ELSET,ELSET=E{matname}\n')
            elnums = [n for n, el in enumerate(elements, start=1) if el[1] == matnum]
            subs = chunks(elnums, 16)
            for sub in subs:
                efile.write(', '.join(str(elnum) for elnum in sub)+',\n')
            logging.info(f'wrote {len(elnums)} elements to set E{matname}')


def main(argv):
    """
    Entry point for mesh2inp.py.

    Arguments:
        argv: command line arguments
    """
    logging.basicConfig(level='INFO', format='%(levelname)s: %(message)s')
    if len(argv) < 3:
        logging.error('mesh2inp.py requires three file names')
        sys.exit(1)
    logging.info(f'reading mesh file {argv[0]}')
    points, elements, materials, edge_boundaries = read_mesh(argv[0])
    logging.info(f'found {len(points)} points')
    logging.info(f'found {len(elements)} elements')
    logging.info(f'found {len(materials)} surface node sets')
    logging.info(f'found {len(edge_boundaries)} edge node sets')
    write_nodes(argv[1], points, elements, materials, edge_boundaries)
    write_elements(argv[2], elements, materials)


if __name__ == '__main__':
    main(sys.argv[1:])
