"""
Class for the Centroidal Voronoi Tesseletion

.. todo::
	- add the show method
	- find a more suitable error estimator for the scalar triangulation

"""
import numpy as np
import math
from scipy.spatial import Delaunay
from scipy import interpolate

class Cvt(object):
	"""
	Documentation
	
	:param numpy.ndarray mu_values: values of the parameters representing the vertices 
		of the triangulation of the parametric domain.
	:param numpy.ndarray pod_basis: basis extracted from the proper orthogonal decomposition.
	:param numpy.ndarray snapshots: database of the output of interest.
	:param numpy.ndarray weights: array of the weights for the computation of the error between
		high fidelity and reconstructed error. Tipically, it is the area/volume of each cell of
		the domain.
	
	:cvar numpy.ndarray mu_values: values of the parameters representing the vertices 
		of the triangulation of the parametric domain.
	:cvar numpy.ndarray pod_basis: basis extracted from the proper orthogonal decomposition.
	:cvar numpy.ndarray snapshots: database of the output of interest.
	:cvar numpy.ndarray weights: array of the weights for the computation of the error between
		high fidelity and reconstructed error. Tipically, it is the area/volume of each cell of
		the domain.
	:cvar int dim_out: dimension of the output of interest.
	:cvar int dim_db: number of the output of interest on the snapshot matrix (dimension of the database).
	:cvar float rel_error: coefficient to make the computed errors relative to the magnitude of the output.
		If the output is a field, it is computed as the L2 value of the first snapshot, if the output is a
		scalar, it is the absolute value of the first snapshot.
	:cvar float max_error: max error of the leave-one-out strategy on the present outputs in the snapshots
		array.
	:cvar int dim_mu: dimension of the parametric space.
	
	"""
	
	def __init__(self, mu_values, snapshots, pod_basis=None, weights=None):
		self.mu_values = mu_values
		self.pod_basis = pod_basis
		self.snapshots = snapshots
		self.weights   = weights
		self.dim_out, self.dim_db = self.snapshots.shape
		
		ref_solution = self.snapshots[:,0]
		if self.weights is not None:
			self.rel_error = np.sqrt(np.sum(np.power(ref_solution* self.weights,2)))
		else:
			self.rel_error = np.abs(ref_solution)
		
		self.max_error = None
		self.dim_mu    = mu_values.shape[0]
		

	@staticmethod
	def _compute_simplex_volume(simplex_vertices):
		"""
		Method implementing the computation of the volume of a N dimensional simplex. 
		Source from wikipedia https://en.wikipedia.org/wiki/Simplex
	
		:param numpy.ndarray simplex_vertices: Nx3 array containing the parameter values representing the vertices of a simplex.
			N is the dimensionality of the parameters.
		
		:return: volume: N dimensional volume of the simplex.
		:rtype: float
		"""

		vertex_0 = simplex_vertices[:,0]
		vertex_0 = np.array([vertex_0])

		simplex_vertices = np.delete(simplex_vertices, 0, 1)
		par_dim = simplex_vertices.shape[1]

		distance = simplex_vertices-np.dot(vertex_0.T,np.ones([1,par_dim]))
		volume = np.abs(np.linalg.det(distance)/math.factorial(par_dim))

		return volume
		
		
	def loo_error(self):
		"""
		Compute the error for each parametric point as projection of the snapshot onto the POD basis
		with a leave-one-out (loo) strategy.
		
		:return: l2_error: error array of the leave-one-out strategy.
		:rtype: numpy.ndarray
		
		"""
		
		l2_error = np.zeros(self.dim_db)

		for j in range(0,self.dim_db):
			
			remaining_snaps = np.delete(self.snapshots, j, 1)
			
			if self.weights is not None:
				weighted_remaining_snaps = np.sqrt(self.weights)*remaining_snaps.T
				eigenvectors,__,__ = np.linalg.svd(weighted_remaining_snaps.T, full_matrices=False)
				loo_basis = np.transpose(np.power(self.weights,-0.5)*eigenvectors.T)
			
				projection = np.zeros(self.dim_out)
				snapshot   = self.snapshots[:,j]

				for i in range(0,self.dim_db-1):
					projection += np.dot(snapshot*self.weights, loo_basis[:,i])*loo_basis[:,i]

				error = (snapshot - projection) * self.weights
				l2_error[j] = np.sqrt(np.sum(np.power(error,2)))/self.rel_error
			else:
				remaining_mu = np.delete(self.mu_values, j, 1)
				remaining_tria = interpolate.LinearNDInterpolator(np.transpose(remaining_mu[:,:]), remaining_snaps[0,:])
				projection = remaining_tria.__call__(self.mu_values[:,j])
				
				if projection is not float:
					projection = np.sum(remaining_snaps)/(self.dim_db-1)
				l2_error[j] = np.abs(self.snapshots[:,j] - projection)/self.rel_error

		return l2_error
		
		
	def add_new_point(self):
		"""
		This method add the new parametric point for the new output to be computed and added to the
		snapshots array. The point is chosen as the baricentric point of the worst approximated simplex
		by the already computed pod basis.
		
		:return: tria: Delaunay triangulation of the parametric points and leave-one-out error.
		:rtype: scipy.spatial.Delaunay
		"""
		
		l2_error = self.loo_error()
		self.max_error = np.max(l2_error)
		
		tria = Delaunay(np.transpose(self.mu_values))
		simplex = tria.simplices
		simp_dim_n = simplex.shape[0]
		error_on_simplex = np.zeros(simp_dim_n)
	
		for i in range(0,simp_dim_n):
			points_of_simplex = self.mu_values[:,simplex[i]]
			volume = self._compute_simplex_volume(points_of_simplex)
			error_on_simplex[i] = np.sum(l2_error[simplex[i]])*volume

		worst_tria_ind    = np.argmax(error_on_simplex)
		worst_tria_points = self.mu_values[:,simplex[worst_tria_ind]]
		worst_tria_err    = l2_error[simplex[worst_tria_ind]]
		new_point = np.zeros(self.dim_mu)
		
		for i in range (0,self.dim_mu):
			new_point[i] = np.sum(np.dot(worst_tria_points[i,:], worst_tria_err))/np.sum(worst_tria_err)
			
		self.mu_values = np.append(self.mu_values, np.transpose([new_point]), 1)
		tria = Delaunay(np.transpose(self.mu_values))

		return tria



