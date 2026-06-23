import igraph as ig
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from pathlib import Path
from visualization_utils import *
import sys

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
GROUP = ['A', 'B']
def load_graph(filename: str="") -> ig.Graph:
    """loads the graph with IGRAPH
    filename: the path to graph
    """
    if not filename:
        filename = DATA_DIR + DEFAULT_GRAPH
    return ig.Graph.Read_GraphML(filename)

def barra_avanzamento(i, totale):
    """Mostra la barra di avanzamento usando solo l'indice e il totale."""
    lunghezza = 30
    percentuale = int((i / totale) * 100)
    blocchi = int((i / totale) * lunghezza)
    
    # Costruisce l'output grafico
    barra = f"\r[{'#' * blocchi}{'-' * (lunghezza - blocchi)}] {percentuale}% ({i}/{totale})"
    
    # Aggiorna la riga nel terminale
    sys.stdout.write(barra)
    sys.stdout.flush()

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


    return n_A, n_B, p, q

def mixing_matrix(G: ig.Graph, 
                  partition: np.ndarray | None = None, 
                  normalized: bool = True):
    '''Calcolo della matrice di mixing
    Questa funzione calcola la matrice di mixing in base alla partizione in ingresso se c'è il parametro partition
    Se Normalized=False, restituisce i conteggi degli archi, altrimenti il loro valore normalizzato per il numero totale di edges'''
    
    
    edgelist = G.get_edgelist()

    if partition is not None:
        
        q = 2
        M = np.zeros((q, q))
        labels = list(range(q))
        for u, v in edgelist:
            r, s = partition[u], partition[v]
            M[r, s] += 1
            if r != s:
                M[s, r] += 1
    
    # calcolo la matrice di mixing usando la partizione di default definita dalle comunità A e B
    else:
        labels = sorted(set(G.vs['group'])) # [A, B]
        label_idx = {l: i for i, l in enumerate(labels)} # {'A': 0, 'B': 1}
        n = len(labels)
        M = np.zeros((n, n))

        for u, v in edgelist:
            r = label_idx[G.vs[u]['group']]
            s = label_idx[G.vs[v]['group']]
            if r == s:
                M[r, r] += 1
            else:
                M[r, s] += 1
                M[s, r] += 1    
    
    if normalized:
        M = M / (M[0, 0] + M[0, 1] + M[1, 1])

    return M, labels


def plot_mixing_matrix(G, M, labels, title=''):

    
    fig, ax = plt.subplots(figsize=(5, 4))

    im = ax.imshow(M, cmap=CMAP_HEAT, vmin=0, vmax=M.max())
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(GROUP, fontsize=13)
    ax.set_yticklabels(GROUP, fontsize=13)
    ax.set_xlabel('Gruppo', fontsize=12)
    ax.set_ylabel('Gruppo', fontsize=12)
    ax.set_title('Mixing matrix' + title)

    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f'{M[i,j]:.3f}',
                    ha='center', va='center',
                    color='white' if M[i,j] > M.max()*0.6 else 'black',
                    fontsize=10)

    plt.colorbar(im, ax=ax, label='Frazione di archi')
    plt.tight_layout()
    plt.show()

def cross_type_fraction(G: ig.Graph, attr_map):
    '''Calcola la frazione di edge tra le comunità '''
    cross = sum(1 for u, v in G.get_edgelist() if attr_map[u] != attr_map[v])
    return cross / G.ecount()

def subgraph_core(G: ig.Graph, K_core: int, plot=True):
    '''Seleziona un sottografo di nodi di un certo K_core in input
    plot=True stampa il sottografo'''
    mask =  [k >= K_core for k in G.vs['coreness']]
    subgraph_core = G.subgraph(np.arange(G.vcount())[mask])
    #print(f"Il core ha k = {K_core} e contiene {subgraph_core.vcount()} nodi.")
    if plot:
        plot_group_AB(subgraph_core, save=False, only_periphery=False, niter=None)
        plt.show()
        
    return subgraph_core    