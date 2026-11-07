"""Geometry-format regression tests with independently known volume/topology."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/anatomy'))
from mesh_sources import tetra_boundary, load_tetgen_boundary
from section_geometry import closed_polygons

class TetraBoundaryTests(unittest.TestCase):
    def test_single_cell_has_outward_unit_simplex_boundary(self):
        p = np.array([[0., 0, 0], [1., 0, 0], [0., 1, 0], [0., 0, 1]])
        data = tetra_boundary(p, np.arange(4), [[0, 1, 2, 3]])
        mesh = trimesh.Trimesh(data['points'], data['faces'], process=False)
        self.assertTrue(mesh.is_watertight and mesh.is_winding_consistent)
        self.assertAlmostEqual(mesh.volume, 1 / 6)
        self.assertEqual(len(mesh.faces), 4)

    def test_shared_internal_face_is_absent(self):
        p = np.array([[0., 0, 0], [1., 0, 0], [0., 1, 0], [0., 0, 1], [0., 0, -1]])
        data = tetra_boundary(p, np.arange(5), [[0, 1, 2, 3], [0, 1, 2, 4]])
        mesh = trimesh.Trimesh(data['points'], data['faces'], process=False)
        self.assertTrue(mesh.is_watertight and mesh.is_winding_consistent)
        self.assertEqual(len(mesh.faces), 6)
        self.assertAlmostEqual(mesh.volume, 1 / 3)

    def test_duplicate_cell_rejected_regardless_of_order(self):
        p = np.eye(4, 3)
        with self.assertRaisesRegex(ValueError, 'Duplicate source tetrahedron'):
            tetra_boundary(p, np.arange(4), [[0, 1, 2, 3], [3, 2, 1, 0]])

    def test_tetgen_zero_based_identity_and_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            node, ele = Path(directory) / 'a.node', Path(directory) / 'a.ele'
            node.write_text('# zero-based native file\n4 3 0 0\n0 0 0 0\n1 1 0 0\n2 0 1 0\n3 0 0 1\n')
            ele.write_text('1 4 0\n0 0 1 2 3 # cell identity is not a node\n')
            data = load_tetgen_boundary(node, ele)
            self.assertEqual(set(data['sourceNodeIds']), {0, 1, 2, 3})
            self.assertEqual(len(data['faces']), 4)
            node.write_text(node.read_text().replace('4 3 0 0', '5 3 0 0'))
            with self.assertRaisesRegex(AssertionError, 'Truncated'):
                load_tetgen_boundary(node, ele)

class SectionTests(unittest.TestCase):
    def test_weld_preserves_a_hole(self):
        rings = [np.array([[0., 0], [3, 0], [3, 3], [0, 3]]), np.array([[1., 1], [2, 1], [2, 2], [1, 2]])]
        segments = np.array([[q[i], q[(i + 1) % 4]] for q in rings for i in range(4)])
        segments[0, 1] += 1e-11
        polygons, record = closed_polygons(segments)
        self.assertEqual(sum(len(p.interiors) for p in polygons), 1)
        self.assertLess(record['maximumEndpointWeld_m'], 1e-8)

    def test_an_open_contour_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'unclosed'):
            closed_polygons(np.array([[[0., 0], [1, 0]], [[1., 0], [1, 1]]]))

if __name__ == '__main__':
    unittest.main()
