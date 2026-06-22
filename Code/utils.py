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

def load_all_centralities(G: ig.Graph, dumpfile: str="") -> dict:
    """calcola le misure di centralità normalizzate e le carica come labels nel grafo
    dumpfile: Se presente viene generato un nuovo file graphml con il grafo aggiornato
    Return: Il dizionario delle centralità calcolate
    """
    N = G.vcount()
    
    denom_betw = ((N - 1) * (N - 2)) / 2
    assert denom_betw != 0, "Grafo con insufficenti nodi"
    
    centralities = {
        'degree':  np.array(G.degree()) / (N - 1),
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

def compute_ccdf(data: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    N = len(data)
    x_values = np.linspace(0,data.max(),5000)
    ccdf = np.array([np.sum(data>x) / N for x in x_values])
    return x_values, ccdf

def node_attr(G, attr, fallback="?"):
    if attr in G.vertex_attributes():
        return [v[attr] if v[attr] is not None else fallback for v in G.vs]
    return [fallback] * G.vcount()



def neighborhood_overlap(G, u, v):
    neighbors_u = set(G.neighbors(u)) - {v}
    neighbors_v = set(G.neighbors(v)) - {u}
    common = neighbors_u & neighbors_v
    union  = neighbors_u | neighbors_v
    return len(common) / len(union) if union else 0.0

def bridge_role(h_u, h_v):
    is_core_u = 'CORE' in str(h_u)
    is_core_v = 'CORE' in str(h_v)
    cores = is_core_u + is_core_v
    if cores == 2:   return 'Core–Core'
    elif cores == 1: return 'Core–Periphery'
    else:            return 'Periphery–Periphery'

