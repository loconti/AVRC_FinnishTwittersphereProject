import igraph as ig
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from pathlib import Path

MAIN_DIR = Path(__file__).parent.parent

DATA_DIR = str(MAIN_DIR / "Data") + '/'
VISUAL_DIR = str(MAIN_DIR / "Visual") + '/'
DEFAULT_GRAPH = "climate_19.graphml"
GROUP = ['A', 'B']

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

def load_all_centralities(G: ig.Graph, dumpfile: str="") -> dict:
    """calcola le misure di centralità normalizzate e le carica come labels nel grafo
    dumpfile: Se presente viene generato un nuovo file graphml con il grafo aggiornato
    Return: Il dizionario delle centralità calcolate
    """
    N = G.vcount()
    
    denom_betw = ((N - 1) * (N - 2)) / 2
    assert denom_betw != 0, "Grafo con insufficenti nodi"
    
    centralities = {
        'degree':  np.array(G.degree()),
        'eigenvector': np.array(G.eigenvector_centrality(scale=True)),
        'closeness' : np.array(G.closeness(normalized=True)),
        'betweenness' : np.array(G.betweenness()) / denom_betw,
        'coreness' : np.array(G.coreness())
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

def ei_index(G: ig.Graph, attr_map):
    edge_type = [attr_map[u] == attr_map[v] for u, v in G.get_edgelist()]
    I = sum(edge_type)
    E = sum(map(lambda x: not x, edge_type))
    return (E - I)/(E + I)

def cross_type_fraction(G: ig.Graph, attr_map):
    cross = sum(1 for u, v in G.get_edgelist() if attr_map[u] != attr_map[v])
    return cross / G.ecount()

def nodes_all(G: ig.Graph) -> np.ndarray[int]:
    return np.arange(G.vcount(), dtype=int)

cmap = plt.get_cmap('tab10')