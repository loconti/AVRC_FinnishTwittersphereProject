import igraph as ig
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from pathlib import Path

MAIN_DIR = Path(__file__).parent.parent

DATA_DIR = str(MAIN_DIR / "Data") + '/'
VISUAL_DIR = str(MAIN_DIR / "Visual") + '/'
DEFAULT_GRAPH = "climate_19.graphml"

GRAPH_FILENAMES = [
    'climate_19.graphml', 'economy_19.graphml', 'education_19.graphml', 'immigration_19.graphml', 'social_19.graphml',
    'climate_23.graphml', 'economy_23.graphml', 'education_23.graphml', 'immigration_23.graphml', 'social_23.graphml'
    ]

def load_graph(filename: str="") -> ig.Graph:
    """loads the graph with IGRAPH
    filename: the path to graph
    """
    if not filename:
        filename = DATA_DIR + DEFAULT_GRAPH
    return ig.Graph.Read_GraphML(filename)

def load_all_centralities(G: ig.Graph, dumpfile: str=""):
    centralities = {
        'degree':  np.array(G.degree()),
        'eigenvector': np.array(G.eigenvector_centrality()),
        'closeness' : np.array(G.closeness()),
        'betweenness' : np.array(G.betweenness())
    }

    for cent in centralities:
        G.vs[cent] = centralities[cent]

    if dumpfile:
        G.write_graphml(dumpfile)

    return centralities

def compute_ccdf(data: np.ndarray, xmin=1) -> tuple[np.ndarray,np.ndarray]:
    N = len(data)

    x_values = np.linspace(xmin,data.max(),5000)
    ccdf = np.array([np.sum(data>=x) / N for x in x_values])
    return x_values, ccdf

cmap = plt.get_cmap('tab10')

