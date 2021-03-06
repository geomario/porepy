import scipy.sparse as sps
import numpy as np
import unittest
import porepy as pp
from test.integration import setup_grids_mpfa_mpsa_tests as setup_grids
from test.test_utils import permute_matrix_vector


class BiotTest(unittest.TestCase):
    def make_boundary_conditions(self, g):
        bound_faces = g.get_all_boundary_faces()
        bound_flow = pp.BoundaryCondition(
            g, bound_faces.ravel("F"), ["dir"] * bound_faces.size
        )
        bound_mech = pp.BoundaryConditionVectorial(
            g, bound_faces.ravel("F"), ["dir"] * bound_faces.size
        )
        return bound_mech, bound_flow

    def make_initial_conditions(self, g, x0, y0, p0):
        """ Make uniform initial condition vectors.
        """
        initial_displacement = x0 * np.ones((g.dim, g.num_cells))
        initial_displacement[1] = y0
        initial_displacement = initial_displacement.ravel("F")
        initial_pressure = p0 * np.ones(g.num_cells)
        initial_state = np.concatenate((initial_displacement, initial_pressure))
        return initial_displacement, initial_pressure, initial_state

    def test_no_dynamics_2d(self):
        g_list = setup_grids.setup_2d()
        kw_f = "flow"
        kw_m = "mechanics"
        discr = pp.Biot()
        for g in g_list:

            bound_mech, bound_flow = self.make_boundary_conditions(g)

            mu = np.ones(g.num_cells)
            c = pp.FourthOrderTensor(g.dim, mu, mu)
            k = pp.SecondOrderTensor(g.dim, np.ones(g.num_cells))

            bound_val = np.zeros(g.num_faces)
            aperture = np.ones(g.num_cells)

            param = pp.Parameters(g, [kw_f, kw_m], [{}, {}])

            param[kw_f]["bc"] = bound_flow
            param[kw_m]["bc"] = bound_mech
            param[kw_f]["aperture"] = aperture
            param[kw_m]["aperture"] = aperture
            param[kw_f]["second_order_tensor"] = k  # permeability / viscosity
            param[kw_m]["fourth_order_tensor"] = c
            param[kw_f]["bc_values"] = bound_val
            param[kw_m]["bc_values"] = np.tile(bound_val, g.dim)
            param[kw_f]["biot_alpha"] = 1
            param[kw_m]["biot_alpha"] = 1
            param[kw_f]["time_step"] = 1
            param[kw_f]["mass_weight"] = 0  # fluid compressibility * porosity
            param[kw_m]["inverter"] = "python"
            data = {pp.PARAMETERS: param}
            data[pp.DISCRETIZATION_MATRICES] = {kw_f: {}, kw_m: {}}
            A, b = discr.matrix_rhs(g, data)
            sol = np.linalg.solve(A.todense(), b)

            self.assertTrue(np.isclose(sol, np.zeros(g.num_cells * (g.dim + 1))).all())

    #    def test_uniform_displacement(self):
    #        # Uniform displacement in mechanics (enforced by boundary conditions).
    #        # Constant pressure boundary conditions.
    #        g_list = setup_grids.setup_2d()
    #        for g in g_list:
    #            bound_faces = g.get_all_boundary_faces()
    #            bound = bc.BoundaryCondition(g, bound_faces.ravel('F'),
    #                                         ['dir'] * bound_faces.size)
    #            flux, bound_flux, div_flow = self.mpfa_discr(g, bound)
    #
    #            a_flow = div_flow * flux
    #
    #            stress, bound_stress, grad_p, div_d, \
    #                stabilization, bound_div_d, div_mech = self.mpsa_discr(g, bound)
    #
    #            a_mech = div_mech * stress
    #
    #            a_biot = sps.bmat([[a_mech, grad_p],
    #                               [div_d, a_flow + stabilization]])
    #
    #            const_bound_val_mech = 1
    #            bval_mech = const_bound_val_mech * np.ones(g.num_faces * g.dim)
    #            bval_flow = np.ones(g.num_faces)
    #            rhs = np.hstack((-div_mech * bound_stress * bval_mech,
    #                             div_flow * bound_flux * bval_flow\
    #                             + div_flow * bound_div_d * bval_mech))
    #            sol = np.linalg.solve(a_biot.todense(), rhs)
    #
    #            sz_mech = g.num_cells * g.dim
    #            self.assertTrue(np.isclose(sol[:sz_mech],)
    #                              const_bound_val_mech * np.ones(sz_mech)).all()

    def test_face_vector_to_scalar(self):
        # Test of function face_vector_to_scalar
        nf = 3
        nd = 2
        rows = np.array([0, 0, 1, 1, 2, 2])
        cols = np.arange(6)
        vals = np.ones(6)
        known_matrix = sps.coo_matrix((vals, (rows, cols))).tocsr().toarray()
        a = pp.Biot()._face_vector_to_scalar(nf, nd).toarray()
        self.assertTrue(np.allclose(known_matrix, a))

    def test_assemble_biot(self):
        """ Test the assembly of the Biot problem using the assembler.

        The test checks whether the discretization matches that of the Biot class.
        """
        gb = pp.meshing.cart_grid([], [2, 1])
        g = gb.grids_of_dimension(2)[0]
        d = gb.node_props(g)
        # Parameters identified by two keywords
        kw_m = "mechanics"
        kw_f = "flow"
        bound_mech, bound_flow = self.make_boundary_conditions(g)
        initial_disp, initial_pressure, initial_state = self.make_initial_conditions(
            g, x0=0, y0=0, p0=0
        )
        state = {
            "displacement": initial_disp,
            "bc_values": np.zeros(g.num_faces * g.dim),
        }
        parameters_m = {"bc": bound_mech, "biot_alpha": 1, "state": state}

        parameters_f = {"bc": bound_flow, "biot_alpha": 1, "state": initial_pressure}
        pp.initialize_default_data(g, d, kw_m, parameters_m)
        pp.initialize_default_data(g, d, kw_f, parameters_f)
        # Discretize the mechanics related terms using the Biot class
        d["state"] = initial_state
        biot_discretizer = pp.Biot()
        biot_discretizer._discretize_mech(g, d)

        # Set up the structure for the assembler. First define variables and equation
        # term names.
        v_0 = "displacement"
        v_1 = "pressure"
        term_00 = "stress_divergence"
        term_01 = "pressure_gradient"
        term_10 = "displacement_divergence"
        term_11_0 = "fluid_mass"
        term_11_1 = "fluid_flux"
        term_11_2 = "stabilization"
        d[pp.PRIMARY_VARIABLES] = {v_0: {"cells": g.dim}, v_1: {"cells": 1}}
        d[pp.DISCRETIZATION] = {
            v_0: {term_00: pp.Mpsa(kw_m)},
            v_1: {
                term_11_0: pp.MassMatrix(kw_f),
                term_11_1: pp.Mpfa(kw_f),
                term_11_2: pp.BiotStabilization(kw_f),
            },
            v_0 + "_" + v_1: {term_01: pp.GradP(kw_m)},
            v_1 + "_" + v_0: {term_10: pp.DivD(kw_m)},
        }
        # Assemble. Also discretizes the flow terms (fluid_mass and fluid_flux)
        general_assembler = pp.Assembler()
        A, b, block_dof, full_dof = general_assembler.assemble_matrix_rhs(gb)

        # Re-discretize and assemble using the Biot class
        A_class, b_class = biot_discretizer.matrix_rhs(g, d, discretize=False)

        # Make sure the variable ordering of the matrix assembled by the assembler
        # matches that of the Biot class.
        grids = [g, g]
        variables = [v_0, v_1]
        A, b = permute_matrix_vector(A, b, block_dof, full_dof, grids, variables)

        # Compare the matrices and rhs vectors
        self.assertTrue(np.all(np.isclose(A.A, A_class.A)))
        self.assertTrue(np.all(np.isclose(b, b_class)))

    def test_assemble_biot_rhs_transient(self):
        """ Test the assembly of a Biot problem with a non-zero rhs using the assembler.

        The test checks whether the discretization matches that of the Biot class and
        that the solution reaches the expected steady state.
        """
        gb = pp.meshing.cart_grid([], [3, 3], physdims=[1, 1])
        g = gb.grids_of_dimension(2)[0]
        d = gb.node_props(g)

        # Parameters identified by two keywords. Non-default parameters of somewhat
        # arbitrary values are assigned to make the test more revealing.
        kw_m = "mechanics"
        kw_f = "flow"
        bound_mech, bound_flow = self.make_boundary_conditions(g)
        val_mech = np.ones(g.dim * g.num_faces)
        val_flow = np.ones(g.num_faces)
        initial_disp, initial_pressure, initial_state = self.make_initial_conditions(
            g, x0=1, y0=2, p0=0
        )
        dt = 1e0
        biot_alpha = 0.6

        state = {"displacement": initial_disp, "bc_values": val_mech}
        parameters_m = {
            "bc": bound_mech,
            "bc_values": val_mech,
            "time_step": dt,
            "biot_alpha": biot_alpha,
            "state": state,
        }
        parameters_f = {
            "bc": bound_flow,
            "bc_values": val_flow,
            "time_step": dt,
            "biot_alpha": biot_alpha,
            "state": initial_pressure,
            "mass_weight": 0.1 * np.ones(g.num_cells),
        }
        pp.initialize_default_data(g, d, kw_m, parameters_m)
        pp.initialize_default_data(g, d, kw_f, parameters_f)

        # Initial condition fot the Biot class
        d["state"] = initial_state

        # Discretize the mechanics related terms using the Biot class
        biot_discretizer = pp.Biot()
        biot_discretizer._discretize_mech(g, d)

        # Set up the structure for the assembler. First define variables and equation
        # term names.
        v_0 = "displacement"
        v_1 = "pressure"
        term_00 = "stress_divergence"
        term_01 = "pressure_gradient"
        term_10 = "displacement_divergence"
        term_11_0 = "fluid_mass"
        term_11_1 = "fluid_flux"
        term_11_2 = "stabilization"
        d[pp.PRIMARY_VARIABLES] = {v_0: {"cells": g.dim}, v_1: {"cells": 1}}
        d[pp.DISCRETIZATION] = {
            v_0: {term_00: pp.Mpsa(kw_m)},
            v_1: {
                term_11_0: ImplicitMassMatrix(kw_f),
                term_11_1: ImplicitMpfa(kw_f),
                term_11_2: pp.BiotStabilization(kw_f),
            },
            v_0 + "_" + v_1: {term_01: pp.GradP(kw_m)},
            v_1 + "_" + v_0: {term_10: pp.DivD(kw_m)},
        }

        times = np.arange(5)
        for _ in times:
            # Assemble. Also discretizes the flow terms (fluid_mass and fluid_flux)
            general_assembler = pp.Assembler()
            A, b, block_dof, full_dof = general_assembler.assemble_matrix_rhs(gb)

            # Assemble using the Biot class
            A_class, b_class = biot_discretizer.matrix_rhs(g, d, discretize=False)

            # Make sure the variable ordering of the matrix assembled by the assembler
            # matches that of the Biot class.
            grids = [g, g]
            variables = [v_0, v_1]
            A, b = permute_matrix_vector(A, b, block_dof, full_dof, grids, variables)

            # Compare the matrices and rhs vectors
            self.assertTrue(np.all(np.isclose(A.A, A_class.A)))
            self.assertTrue(np.all(np.isclose(b, b_class)))

            # Store the current solution for the next time step.
            # First for the assembler version
            x_i = sps.linalg.spsolve(A_class, b_class)
            u_i = x_i[: (g.dim * g.num_cells)]
            p_i = x_i[(g.dim * g.num_cells) :]
            d[pp.PARAMETERS][kw_m]["state"]["displacement"] = u_i
            d[pp.PARAMETERS][kw_f]["state"] = p_i
            # ... and then for the Biot class
            d["state"] = x_i

        # Check that the solution has converged to the expected, uniform steady state
        # dictated by the BCs.
        self.assertTrue(np.all(np.isclose(x_i, np.ones((g.dim + 1) * g.num_cells))))


class ImplicitMassMatrix(pp.MassMatrix):
    def assemble_rhs(self, g, data):
        """ Overwrite MassMatrix method to return the correct rhs for an IE time
        discretization of the Biot problem.

        TODO: Implement a more general solution.
        """
        parameter_dictionary = data[pp.PARAMETERS][self.keyword]
        matrix_dictionary = data[pp.DISCRETIZATION_MATRICES][self.keyword]
        previous_pressure = parameter_dictionary["state"]
        return matrix_dictionary["mass"] * previous_pressure


class ImplicitMpfa(pp.Mpfa):
    def assemble_matrix_rhs(self, g, data):
        """ Overwrite MPSA method to be consistent with the Biot dt convention.

        TODO: Implement more general solution?
        """
        a, b = super().assemble_matrix_rhs(g, data)
        dt = data[pp.PARAMETERS][self.keyword]["time_step"]
        return a * dt, b * dt


if __name__ == "__main__":
    unittest.main()
