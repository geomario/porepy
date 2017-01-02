import numpy as np
import unittest

from compgeom import basics

#------------------------------------------------------------------------------#

class BasicsTest( unittest.TestCase ):

#------------------------------------------------------------------------------#

    def test_compute_normal_2d( self ):
        pts = np.array( [ [ 0., 2., -1 ],
                          [ 0., 4.,  2 ] ] )
        normal = basics.compute_normal( pts )
        normal_test = np.array([0.,0.,1.])
        pt = basics.to_3d_pt( pts[:,0] )

        assert np.allclose( np.linalg.norm( normal ), 1. )
        assert np.allclose( [ np.dot( normal, p - pt ) \
                              for p in basics.to_3d(pts[:,1:]).T ],
                            np.zeros( pts.shape[1] - 1 )  )
        assert np.allclose( normal, normal_test )

#------------------------------------------------------------------------------#

    def test_compute_normal_3d( self ):
        pts = np.array( [ [  2.,  0.,  1.,  1. ],
                          [  1., -2., -1.,  1. ],
                          [ -1.,  0.,  2., -8. ] ] )
        normal_test = np.array( [7., -5., -1.] )
        normal_test = normal_test / np.linalg.norm( normal_test )
        normal = basics.compute_normal( pts )
        pt = pts[:,0]

        assert np.allclose( np.linalg.norm( normal ), 1. )
        assert np.allclose( [ np.dot( normal, p - pt ) \
                              for p in pts[:,1:].T ],
                            np.zeros( pts.shape[1] - 1 )  )
        assert np.allclose( normal, normal_test ) or \
               np.allclose( normal, -1. * normal_test )

#------------------------------------------------------------------------------#

    def test_project_plane( self ):
        pts = np.array( [ [  2.,  0.,  1.,  1. ],
                          [  1., -2., -1.,  1. ],
                          [ -1.,  0.,  2., -8. ] ] )
        R = basics.project_plane_matrix( pts )
        P_pts = np.array( [ np.dot( R, p ) for p in pts.T ] ).T

        assert np.allclose( P_pts[2,:], 1.15470054 * np.ones(4) )

#------------------------------------------------------------------------------#
