import igraph as ig
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from pathlib import Path
import sys

from visualization_utils import *

MAIN_DIR = Path(__file__).parent

DATA_DIR = str(MAIN_DIR / "Data") + '/'
JSON_DIR = DATA_DIR + 'JSON/'
CENTRALITY_DIR = DATA_DIR + 'Centrality/'

GRAPH_FILENAMES = [
    'climate_19.graphml', 'economy_19.graphml', 'education_19.graphml', 'immigration_19.graphml', 'social_19.graphml',
    'climate_23.graphml', 'economy_23.graphml', 'education_23.graphml', 'immigration_23.graphml', 'social_23.graphml'
    ]
TOPIC = ['Climate', 'Economy','Education', 'Immigration', 'Social']
YEARS = [2019]*5 + [2023]*5
GROUP = ['A', 'B']

def load_graph(filename: str="") -> ig.Graph:
    """ Carica il grafo con igraph
    filename: path 
    """
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
    """Calcola le metriche globali della rete 
    return: dizionario con le metriche """
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
    '''Calcola la complementary cumulative function 
    data: array numpy dei dati
    xmin: valore minimo da cui iniziamo a calcolare la ccdf
    return: valori di x, ccdf'''
    N = len(data)

    x_values = np.linspace(xmin, data.max(), 5000)
    ccdf = np.array([np.sum(data>=x) / N for x in x_values])
    return x_values, ccdf

def neighborhood_overlap(G, u, v) -> float:
    '''Calcola il neigborhood overlap tra due nodi u e v'''
    neighbors_u = set(G.neighbors(u)) - {v}
    neighbors_v = set(G.neighbors(v)) - {u}
    common = neighbors_u & neighbors_v  # intersect
    union  = neighbors_u | neighbors_v  # union
    return len(common) / len(union) if union else 0.0

def make_edges_df(G: ig.Graph) -> pd.DataFrame:
    """Dataframe degli edges, classificati come bridge o internal
    overlap == 0 definisce i local bridge
    """
    rows = []
    for edge in G.es:
        u = edge.source
        v = edge.target
        g_u = G.vs['group'][u]
        g_v = G.vs['group'][v]

        overlap = neighborhood_overlap(G, u, v)
        rows.append({
            "node_u"         : u,
            "node_v"         : v,
            "id_u"           : G.vs["id"][u],
            "id_v"           : G.vs["id"][v],
            "group_u"        : g_u,
            "group_v"        : g_v,  
            "edge_type"      : "bridge" if g_u != g_v else "internal",
            "overlap"        : overlap
        })

    return pd.DataFrame(rows)


def ei_index(G: ig.Graph, attr_map) -> float:
    """Calcolo dell'EI-index data la partizione dei nodi in due gruppi (attr_map)
    """
    edge_type = [attr_map[u] == attr_map[v] for u, v in G.get_edgelist()]
    I = sum(edge_type)
    E = sum(map(lambda x: not x, edge_type))


    return (E - I)/(E + I)

def communities_statistics(G: ig.Graph):
    """Return: - il numero di nodi per la comunità A e B
               - la probabilità che un nodo appartenga ad A
               - la probabilità che un nodo appartenga a B
    """
    n = G.vcount()
    n_A = len(G.vs.select(group="A"))
    n_B = len(G.vs.select(group="B"))

    p = n_A / n
    q = 1 - p


    return n_A, n_B, p, q

def mixing_matrix(G: ig.Graph, 
                  partition: np.ndarray, 
                  normalized: bool = True):
    '''Calcolo della matrice di mixing
    Questa funzione calcola la matrice di mixing in base alla partizione (partition) in ingresso 
    Se Normalized=False, restituisce i conteggi degli archi, altrimenti il loro valore normalizzato per il numero totale di edges'''
    
    
    edgelist = G.get_edgelist()

    q = 2
    M = np.zeros((q, q))
    labels = list(range(q))
    for u, v in edgelist:
        r, s = partition[u], partition[v]
        M[r, s] += 1
        if r != s:
            M[s, r] += 1
    
    
    
    if normalized:
        M = M / (M[0, 0] + M[0, 1] + M[1, 1])

    return M, labels


def plot_mixing_matrix(M, labels, title=''):
    ''' Stampa la matrice di mixing
    M: mixing matrix
    labels: etichette dei gruppi '''
    
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

def cross_type_fraction(G: ig.Graph, attr_map) -> float:
    '''Calcola la frazione di edge tra le comunità data una partizione (attr_map)'''
    cross = sum(1 for u, v in G.get_edgelist() if attr_map[u] != attr_map[v])
    return cross / G.ecount()

def subgraph_core(G: ig.Graph, K_core: int, plot=True) -> ig.Graph:
    '''Genera un sottografo con nodi nel K_core
    plot=True: stampa il sottografo'''
    mask =  [k >= K_core for k in G.vs['coreness']]
    subgraph_core = G.subgraph(np.arange(G.vcount())[mask])
    #print(f"Il core ha k = {K_core} e contiene {subgraph_core.vcount()} nodi.")
    if plot:
        plot_group_AB(subgraph_core, save=False, only_periphery=False, niter=None)
        plt.show()
        
    return subgraph_core    