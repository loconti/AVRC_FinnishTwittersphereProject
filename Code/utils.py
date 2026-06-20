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
TOPIC = ['Climate', 'Economy','Education', 'Immigration', 'Social']
YEARS = [2019]*5 + [2023]*5
def load_graph(filename: str="") -> ig.Graph:
    """loads the graph with IGRAPH
    filename: the path to graph
    """
    if not filename:
        filename = DATA_DIR + DEFAULT_GRAPH
    return ig.Graph.Read_GraphML(filename)

def network_statistics(G: ig.Graph) -> dict:
    """Calcola le metriche globali della rete e le stampa"""
    N = G.vcount()
    L = G.ecount()
    rho = G.density()
    avg_degree = 2 * L / N
    avg_clustering = G.transitivity_avglocal_undirected() # coefficiente di clustering medio
    diametro = G.diameter() # diametro del grafo
    apl = G.average_path_length(directed=False) # cammino medio

    stat = {
        "Numero di Nodi": N,
        "Numero di Archi": L,
        "Densità del Grafo": rho,
        "Grado Medio": avg_degree,
        "Clustering Medio": avg_clustering,
        "Diametro": diametro, 
        "Cammino Medio": apl
    }
    return stat


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

def ei_index(G: ig.Graph, attr_map) -> float:
    """Calcolo dell'EI-index data la partizione dei nodi in due gruppi
    """
    edge_type = [attr_map[u] == attr_map[v] for u, v in G.get_edgelist()]
    I = sum(edge_type)
    E = sum(map(lambda x: not x, edge_type))


    return (E - I)/(E + I)

def communities_statistics(G: ig.Graph):
    """Return: - il numero di nodi per la comunità A e B
               - la probabilità che un nodo appartenga ad A
               - la probabilità che un nodo appartenga a B
               - 2pq"""
    n = G.vcount()
    n_A = len(G.vs.select(group="A"))
    n_B = len(G.vs.select(group="B"))

    p = n_A / n
    q = 1 - p


    return n_A, n_B, p, q, 2*p*q