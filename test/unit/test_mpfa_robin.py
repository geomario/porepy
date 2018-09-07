import numpy as np
import scipy.sparse as sps
import unittest

import porepy as pp

class RobinBoundTest(unittest.TestCase):
    def test_flow_left_right(self):
        nxs = [1, 3]
        nys = [1, 3]
        for nx in nxs:
            for ny in nys:
                g = pp.CartGrid([nx, ny], physdims=[1, 1])
                g.compute_geometry()
                k = pp.SecondOrderTensor(2, np.ones(g.num_cells))
                alpha = 1.5

                left = g.face_centers[0] < 1e-10
                right = g.face_centers[0] > 1 - 1e-10

                dir_ind = np.ravel(np.argwhere(left))
                rob_ind = np.ravel(np.argwhere(right))

                names = ['dir']*len(dir_ind) + ['rob'] * len(rob_ind)
                bnd_ind = np.hstack((dir_ind, rob_ind))
                bnd = pp.BoundaryCondition(g, bnd_ind, names)

                p_bound = 1
                rob_bound = 0
                C = (rob_bound - alpha*p_bound) / (alpha - p_bound)
                u_ex = - C * g.face_normals[0]
                p_ex = C * g.cell_centers[0] + p_bound
                self.solve_robin(g, k, bnd, alpha, p_bound, rob_bound, dir_ind, rob_ind, p_ex, u_ex)

    def test_flow_nz_rhs(self):
        nxs = [1, 3]
        nys = [1, 3]
        for nx in nxs:
            for ny in nys:
                g = pp.CartGrid([nx, ny], physdims=[1, 1])
                g.compute_geometry()
                k = pp.SecondOrderTensor(2, np.ones(g.num_cells))
                alpha = 1.5

                left = g.face_centers[0] < 1e-10
                right = g.face_centers[0] > 1 - 1e-10

                dir_ind = np.ravel(np.argwhere(left))
                rob_ind = np.ravel(np.argwhere(right))

                names = ['dir']*len(dir_ind) + ['rob'] * len(rob_ind)
                bnd_ind = np.hstack((dir_ind, rob_ind))
                bnd = pp.BoundaryCondition(g, bnd_ind, names)

                p_bound = 1
                rob_bound = 1

                C = (rob_bound - alpha*p_bound) / (alpha - p_bound)
                u_ex = - C * g.face_normals[0]
                p_ex = C * g.cell_centers[0] + p_bound
                self.solve_robin(g, k, bnd, alpha, p_bound, rob_bound, dir_ind, rob_ind, p_ex, u_ex)
    def test_flow_down(self):
        nxs = [1, 3]
        nys = [1, 3]
        for nx in nxs:
            for ny in nys:
                g = pp.CartGrid([nx, ny], physdims=[1, 1])
                g.compute_geometry()
                k = pp.SecondOrderTensor(2, np.ones(g.num_cells))
                alpha = 1.5

                bot = g.face_centers[1] < 1e-10
                top = g.face_centers[1] > 1 - 1e-10

                dir_ind = np.ravel(np.argwhere(top))
                rob_ind = np.ravel(np.argwhere(bot))

                names = ['dir']*len(dir_ind) + ['rob'] * len(rob_ind)
                bnd_ind = np.hstack((dir_ind, rob_ind))
                bnd = pp.BoundaryCondition(g, bnd_ind, names)

                p_bound = 1
                rob_bound = 1
                C = (rob_bound - alpha*p_bound) / (alpha - p_bound)
                u_ex = C * g.face_normals[1]
                p_ex = C *(1- g.cell_centers[1]) + p_bound
                self.solve_robin(g, k, bnd, alpha, p_bound, rob_bound, dir_ind, rob_ind, p_ex, u_ex)


    def solve_robin(self, g, k, bnd, alpha, p_bound, rob_bound, dir_ind, rob_ind, p_ex, u_ex):
        flux, bound_flux, _, _ = pp.numerics.fv.mpfa._mpfa_local(g, k, bnd, alpha=alpha)

        div = pp.fvutils.scalar_divergence(g)

        u_bound = np.zeros(g.num_faces)
        u_bound[dir_ind] = p_bound
        u_bound[rob_ind] = rob_bound * g.face_areas[rob_ind]


        a = div * flux
        b = -div * bound_flux * u_bound

        p = np.linalg.solve(a.A, b)
        assert np.allclose(p, p_ex)
        assert np.allclose(flux * p + bound_flux * u_bound, u_ex)
