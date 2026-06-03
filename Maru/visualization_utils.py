import igraph as ig
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Patch
from pathlib import Path
from scipy.interpolate import make_interp_spline

# ------------------------------------------------------------
# 1. Caricamento grafo e layout (una sola volta)
# ------------------------------------------------------------
visual_layout_name = {'kk': 'kamada-kawai', 'fr': 'force'}
VISUAL_LAYOUT = 'fr' # puoi cambiare in 'kk' se preferisci
data_dir = Path(__file__).parent / "Data"
visual_dir = Path(__file__).parent / "Visual"
graph_file = data_dir / "climate_19.graphml"
scaling_factor = 15.0
layout = None
coords = np.array(())
cmap = plt.get_cmap('tab10')

# Mapping to core - periphery
mappingCP = {
    'A_CORE': 'Core',
    'B_CORE': 'Core',
    'A_PERIPHERY': 'Periphery',
    'B_PERIPHERY': 'Periphery'
}


# ------------------------------------------------------------
# 2. Archi – struttura condivisa (LineCollection ottimizzata)
# ------------------------------------------------------------


def plot_group_AB(G, layout=None, save=True, only_periphery=False, niter=None, 
                  scaling_factor=1.0, mappingCP=None, visual_dir=Path(".")):
    """
    Colora i nodi in base al gruppo (A o B) con rosso per A, blu per B.
    Se only_periphery=True, isola ed esibisce solo il sottografo della periferia.
    """
    # 1. Gestione del Layout obbligatorio
    if layout is None and niter is None:
        # Se non viene passato un layout, lo calcoliamo sul grafo corrente
        layout_plot = G.layout_fruchterman_reingold(grid='nogrid', niter=500)
    elif niter is not None:
        layout_plot = G.layout_fruchterman_reingold(grid='nogrid', niter=niter)
    else:
        layout_plot = layout

    coords = np.array(layout_plot.coords) * scaling_factor

    # 2. Gestione Sottografo (Isolamento Periferia) con riallineamento coordinate
    if only_periphery:
        if mappingCP is None:
            raise ValueError("mappingCP deve essere fornito se only_periphery=True")
        
        # Trova gli indici dei nodi (nel grafo globale G) che appartengono alla periferia
        periphery_node_indices = [
            v.index for v in G.vs if mappingCP.get(v['hierarchy'], '') == 'Periphery'
        ]
        
        if not periphery_node_indices:
            print("Attenzione: Nessun nodo trovato per la periferia. Mostro il grafo completo.")
            plot_graph = G
            coords_plot = coords
            title_suffix = ""
        else:
            # Crea il sottografo isolato
            plot_graph = G.subgraph(periphery_node_indices)
            # CRITICO: Filtra le coordinate globali mantenendo l'ordine dei nodi del sottografo
            coords_plot = coords[periphery_node_indices]
            title_suffix = "– SOLO PERIFERIA"
    else:
        plot_graph = G
        coords_plot = coords
        title_suffix = ""

    # 3. Estrazione Archi (Adesso gli indici di current_edges corrispondono a coords_plot)
    current_edges = np.array(plot_graph.get_edgelist())
    if len(current_edges) > 0:
        current_segments = np.stack([coords_plot[current_edges[:, 0]], coords_plot[current_edges[:, 1]]], axis=1)
    else:
        current_segments = np.empty((0, 2, 2))

    # 4. Mappatura Colori
    values = plot_graph.vs['group']
    unique_vals = sorted(set(values))
    print(f"Gruppi trovati{title_suffix}: {unique_vals}")

    color_map = {'A': cmap(0), 'B': cmap(3)}
    # Gestione fallback se un nodo non ha gruppo A o B
    node_colors = [color_map.get(v, '#808080') for v in values]

    fig, ax = plt.subplots(figsize=(16, 14))

    # Disegna gli archi
    if len(current_segments) > 0:
        lc = LineCollection(current_segments, colors="black", alpha=0.3, linewidths=0.6, zorder=0)
        ax.add_collection(lc)

    # Nodi
    ax.scatter(coords_plot[:, 0], coords_plot[:, 1], s=50, alpha=0.60,
               c=node_colors, edgecolors='none', zorder=1)

    # Limiti e titolo
    margin = 5
    ax.set_xlim(coords_plot[:, 0].min() - margin, coords_plot[:, 0].max() + margin)
    ax.set_ylim(coords_plot[:, 1].min() - margin, coords_plot[:, 1].max() + margin)
    
    # Rimosse dipendenze da globali per il titolo
    ax.set_title(f"Polarizzazione: GRUPPO (A vs B) {title_suffix}", fontsize=14, fontweight="bold")
    ax.axis("off")

    # Legenda
    legend_elements = [Patch(facecolor=color_map['A'], edgecolor='none', label='Gruppo A'),
                       Patch(facecolor=color_map['B'], edgecolor='none', label='Gruppo B')]
    ax.legend(handles=legend_elements, title="Gruppo",
              loc='upper left', bbox_to_anchor=(1.02, 1), frameon=True)

    # Didascalia metriche (gestione dell'infinito sul diametro se il sottografo è disconnesso)
    try:
        diameter_val = plot_graph.diameter()
    except:
        diameter_val = "N/A (Disconnesso)"

    caption = (f"Nodi: {plot_graph.vcount()} | Archi: {plot_graph.ecount()} | "
               f"Densità: {plot_graph.density():.4f} | Diametro: {diameter_val} | "
               f"Coeff. Clustering: {plot_graph.transitivity_undirected():.4f} | "
               f"Avg Path Length: {plot_graph.average_path_length():.4f}")
    
    plt.figtext(0.5, 0.05, caption, wrap=True, ha='center',
                fontsize=11, fontfamily='monospace',
                bbox={'facecolor': 'none', 'edgecolor': 'gray', 'pad': 10})

    if save:
        visual_dir = Path(visual_dir)
        visual_dir.mkdir(parents=True, exist_ok=True)
        filename = f"graph_group_AB_periphery.png" if only_periphery else f"graph_group_AB.png"
        out_ab = visual_dir / filename
        fig.savefig(out_ab, dpi=300, bbox_inches="tight")
        print(f"✓ Salvato: {out_ab}")
    else:
        plt.show()
    
    plt.close(fig)
    return
