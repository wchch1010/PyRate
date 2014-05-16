'''
Minimum Spanning Tree functionality for PyRate.
Contains functions to calculate MST using interferograms.

Author: Ben Davies, ANUSF
'''

from itertools import product
from numpy import array, nan, isnan, float32, ndarray

from algorithm import get_all_epochs, master_slave_ids
from pygraph.classes.graph import graph
from pygraph.algorithms.minmax import minimal_spanning_tree

# TODO: may need to implement memory saving row-by-row access
# TODO: document weighting by either Nan fraction OR variance


def _remove_root_node(mst):
	"""Discard pygraph's root node from MST dict to conserve memory."""
	for k in mst.keys():
		if mst[k] is None:
			del mst[k]
	return mst


def default_mst(ifgs, noroot=True):
	'''
	Returns default MST dict for the given Ifgs. The MST is calculated using a
	weighting based on the number of incoherent cells in the phase band.
	noroot - True removes the PyGraph default root node from the result.
	'''
	edges = [i.DATE12 for i in ifgs]
	epochs = master_slave_ids(get_all_epochs(ifgs)).keys()
	weights = [i.nan_fraction for i in ifgs]  # NB: other attrs for weights?

	g = graph()
	g.add_nodes(epochs) # each acquisition is a node
	for edge, weight in zip(edges, weights):
		g.add_edge(edge, wt=weight)

	mst = minimal_spanning_tree(g)
	if noroot:
		_remove_root_node(mst)
	return mst


def mst_matrix(ifgs, epochs):
	'''
	Returns array of MST trees from a pixel-by-pixel MST. A MST is calculated
	for each individual pixel, ignoring NODATA values.
	ifgs - sequence of Ifg objs
	epochs = an EpochList object derived from the ifgs
	'''

	# locally cache all edges/weights for on-the-fly graph modification
	edges = [i.DATE12 for i in ifgs]
	weights = [i.nan_fraction for i in ifgs]

	# make default MST to optimise result when no Ifg cells in a stack are nans
	g = graph()
	g.add_nodes(epochs.dates) # each acquisition is a node
	for edge, weight in zip(edges, weights):
		g.add_edge(edge, wt=weight)

	dmst = _remove_root_node(minimal_spanning_tree(g)) # default base MST

	# prepare source and dest data arrays
	num_ifgs = len(ifgs)
	data_stack = array([i.phase_data for i in ifgs], dtype=float32)
	mst_result = ndarray(shape=(i.FILE_LENGTH, i.WIDTH), dtype=object)

	# create MSTs for each pixel in the ifg data stack
	for y, x in product(xrange(i.FILE_LENGTH), xrange(i.WIDTH)):
		values = data_stack[:, y, x] # select stack of all ifg values for a pixel
		nc = sum(isnan(values))

		# optimisations: use precreated results for all nans/no nans
		if nc == 0:
			mst_result[y, x] = dmst
			continue
		elif nc == num_ifgs:
			mst_result[y, x] = nan
			continue

		# otherwise dynamically adjust graph, skipping edges where pixels are NaN
		for value, edge, weight in zip(values, edges, weights):
			if not isnan(value):
				if not g.has_edge(edge):
					g.add_edge(edge, wt=weight)
			else:
				if g.has_edge(edge):
					g.del_edge(edge)

		mst = _remove_root_node(minimal_spanning_tree(g))
		mst_result[y, x] = mst

	return mst_result