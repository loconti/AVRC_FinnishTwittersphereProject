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
coords = np.array(())

def load_graph(filename: str) -> ig.Graph:
    _G = ig.Graph.Read_GraphML(str(graph_file))

    # Layout condiviso per entrambi i plot
    layout = _G.layout(VISUAL_LAYOUT)
    coords = np.array(layout.coords)
    coords = coords * scaling_factor
    return _G

G = load_graph(graph_file)

# Mapping to core - periphery
mappingCP = {
    'A_CORE': 'Core',
    'B_CORE': 'Core',
    'A_PERIPHERY': 'Periphery',
    'B_PERIPHERY': 'Periphery'
}

# Metriche di base (stampate una volta)
print("\n" + "="*50)
print(f"Numero di nodi: {G.vcount()}")
print(f"Numero di archi: {G.ecount()}")
print(f"Densità: {G.density():.5f}")
print(f"Diametro: {G.diameter()}")
print(f"Clustering Coefficient: {G.transitivity_undirected():.4f}")
print(f"Average Path Length: {G.average_path_length():.4f}")
print("="*50 + "\n")

# ------------------------------------------------------------
# 2. Archi – struttura condivisa (LineCollection ottimizzata)
# ------------------------------------------------------------
edges = np.array(G.get_edgelist())
segments = np.stack([coords[edges[:, 0]], coords[edges[:, 1]]], axis=1)

def plot_group_AB(save=True, only_periphery=False, niter=None):
    """
    Colora i nodi in base al gruppo (A o B) con rosso per A, blu per B.
    Se only_periphery=True, isola ed esibisce solo il sottografo della periferia.
    """
    layout_plot = layout
    if niter is not None:
        layout_plot= G.layout_fruchterman_reingold(grid='nogrid', niter=500)
    coords = np.array(layout_plot.coords) * scaling_factor

    # 1. Gestione Sottografo (Isolamento Periferia)
    if only_periphery:
        # Trova gli indici dei nodi che appartengono alla periferia
        periphery_node_indices = [
            v.index for v in G.vs if mappingCP[v['hierarchy']] == 'Periphery'
        ]
        # Crea un vero e proprio sottografo isolato
        plot_graph = G.subgraph(periphery_node_indices)
        # Filtra le coordinate mantenendo solo quelle dei nodi selezionati
        coords_plot = coords[periphery_node_indices]
        title_suffix = "– SOLO PERIFERIA"
    else:
        plot_graph = G
        coords_plot = coords
        title_suffix = ""

    # 2. Estrazione Archi del grafo corrente (fondamentale!)
    current_edges = np.array(plot_graph.get_edgelist())
    if len(current_edges) > 0:
        current_segments = np.stack([coords_plot[current_edges[:, 0]], coords_plot[current_edges[:, 1]]], axis=1)
    else:
        current_segments = np.empty((0, 2, 2))

    # 3. Mappatura Colori
    values = plot_graph.vs['group']
    unique_vals = sorted(set(values))
    print(f"Gruppi trovati{title_suffix}: {unique_vals}")

    color_map = {'A': '#E63946', 'B': '#1E6091'}
    node_colors = [color_map[v] for v in values]

    fig, ax = plt.subplots(figsize=(16, 14))

    # Disegna solo gli archi del (sotto)grafo corrente
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
    ax.set_title(f"Polarizzazione: GRUPPO (A vs B) {title_suffix} – layout {visual_layout_name[VISUAL_LAYOUT]}",
                 fontsize=14, fontweight="bold")
    ax.axis("off")

    # Legenda
    legend_elements = [Patch(facecolor=color_map['A'], edgecolor='none', label='Gruppo A'),
                       Patch(facecolor=color_map['B'], edgecolor='none', label='Gruppo B')]
    ax.legend(handles=legend_elements, title="Gruppo",
              loc='upper left', bbox_to_anchor=(1.02, 1), frameon=True)

    # Didascalia metriche (aggiornate al sottografo se only_periphery=True)
    caption = (f"Nodi: {plot_graph.vcount()} | Archi: {plot_graph.ecount()} | "
               f"Densità: {plot_graph.density():.4f} | Diametro: {plot_graph.diameter()} | "
               f"Coeff. Clustering: {plot_graph.transitivity_undirected():.4f} | "
               f"Avg Path Length: {plot_graph.average_path_length():.4f}")
    plt.figtext(0.5, 0.12, caption, wrap=True, ha='center',
                fontsize=11, fontfamily='monospace',
                bbox={'facecolor': 'none', 'edgecolor': 'gray', 'pad': 10})

    if save:
        filename = f"graPhoto_{VISUAL_LAYOUT}_group_AB_periphery.png" if only_periphery else f"graPhoto_{VISUAL_LAYOUT}_group_AB.png"
        out_ab = visual_dir / filename
        fig.savefig(out_ab, dpi=300, bbox_inches="tight")
        print(f"✓ Salvato: {out_ab}")
    else:
        plt.show()
    plt.close(fig)
    return

# ------------------------------------------------------------
# 4. Funzione per disegnare nucleo vs periferia (aggregazione)
# ------------------------------------------------------------
def plot_core_vs_periphery(save=True):
    """
    Aggrega le quattro categorie di 'hierarchy' in:
      - Core: A_CORE + B_CORE
      - Periphery: A_PERIPHERY + B_PERIPHERY
    Colorazione personalizzata (es. rosso scuro per core, grigio per periferia).
    """
    hierarchy_values = G.vs['hierarchy']
    
    aggregated = [mappingCP[v] for v in hierarchy_values]
    unique_groups = sorted(set(aggregated))
    print(f"Categorie aggregate: {unique_groups}")

    # Colori: Core = rosso bordeaux, Periphery = grigio chiaro
    color_map = {'Core': "#E63946", 'Periphery': '#1E6091'}
    node_colors = [color_map[g] for g in aggregated]

    fig, ax = plt.subplots(figsize=(16, 14))

    # Archi
    lc = LineCollection(segments, colors="black", alpha=0.5, linewidths=0.8, zorder=0)
    ax.add_collection(lc)

    # Nodi
    ax.scatter(coords[:, 0], coords[:, 1], s=50, alpha=0.60,
               c=node_colors, edgecolors='none', zorder=1)

    margin = 5
    ax.set_xlim(coords[:, 0].min() - margin, coords[:, 0].max() + margin)
    ax.set_ylim(coords[:, 1].min() - margin, coords[:, 1].max() + margin)
    ax.set_title(f"Confronto NUCLEO vs PERIFERIA – layout {visual_layout_name[VISUAL_LAYOUT]}",
                 fontsize=14, fontweight="bold")
    ax.axis("off")

    # Legenda
    legend_elements = [
        Patch(facecolor=color_map['Core'], edgecolor='none', label='Nucleo (A_CORE + B_CORE)'),
        Patch(facecolor=color_map['Periphery'], edgecolor='none', label='Periferia (A_PERIPHERY + B_PERIPHERY)')
    ]
    ax.legend(handles=legend_elements, title="Categoria",
              loc='upper left', bbox_to_anchor=(1.02, 1), frameon=True)

    caption = (f"Nodi: {G.vcount()} | Archi: {G.ecount()} | "
               f"Densità: {G.density():.4f} | Diametro: {G.diameter()} | "
               f"Coeff. Clustering: {G.transitivity_undirected():.4f} | "
               f"Avg Path Length: {G.average_path_length():.4f}")
    plt.figtext(0.5, 0.12, caption, wrap=True, ha='center',
                fontsize=11, fontfamily='monospace',
                bbox={'facecolor': 'none', 'edgecolor': 'gray', 'pad': 10})


    if save:
        out_core = visual_dir / f"graPhoto_{VISUAL_LAYOUT}_core_vs_periphery.png"
        fig.savefig(out_core, dpi=300, bbox_inches="tight")
        print(f"✓ Salvato: {out_core}")
    else:
        plt.show()
    plt.close(fig)

    return

def get_smooth_curve(x, y, num_points=300):
    """Prende pochi punti X, Y e restituisce array densi per una curva fluida."""
    # Se ci sono meno di 4 punti, la spline cubica non funziona, ritorniamo i dati grezzi
    if len(x) < 4:
        return x, y
        
    # Creiamo un asse X fittissimo (300 punti)
    x_smooth = np.linspace(x.min(), x.max(), num_points)
    
    # Interpolazione Spline per ammorbidire
    spline = make_interp_spline(x, y, k=3)
    y_smooth = spline(x_smooth)
    
    # Le curve morbide a volte oscillano sotto lo zero: tronchiamo i valori negativi
    y_smooth = np.maximum(y_smooth, 0)
    
    return x_smooth, y_smooth

def plot_degree_distributions(save=True):
    """
    Crea una figura con due pannelli verticali:
    - Sopra: distribuzione per tutti i nodi (linea continua morbida).
    - Sotto: distribuzione per Core e Periferia, con linee continue e aree colorate.
    """
    degrees = np.array(G.degree())
    max_deg = degrees.max()
    
    # ---- CCDF globale ----
    # Calcola la probabilità complementare P(degree > x) per x interi
    x_vals = np.arange(0, max_deg + 2)
    ccdf = np.array([np.sum(degrees > x) / len(degrees) for x in x_vals])
    
    # ---- Separa gradi per core e periphery ----
    hierarchy = G.vs['hierarchy']
    core_mask = [h in ('A_CORE', 'B_CORE') for h in hierarchy]
    periphery_mask = [h in ('A_PERIPHERY', 'B_PERIPHERY') for h in hierarchy]
    
    deg_core = degrees[core_mask]
    deg_periph = degrees[periphery_mask]
    
    # ---- Istogrammi normalizzati (densità di probabilità) ----
    bins = np.arange(0, max_deg + 2) - 0.5   # bin centrati sui valori interi
    bin_centers = (bins[:-1] + bins[1:]) / 2   # x = valore del grado
    hist_core, _ = np.histogram(deg_core, bins=bins, density=True)
    hist_periph, _ = np.histogram(deg_periph, bins=bins, density=True)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12), sharex=True)

    # Ammorbidiamo le curve
    bins_s, ccdf_s = get_smooth_curve(bins, ccdf)
    bin_centers_s, y_core_s = get_smooth_curve(bin_centers, hist_core)
    _, y_peri_s = get_smooth_curve(bin_centers, hist_periph)

    ax1.plot(bins_s, ccdf_s, color='black', linewidth=2.5)
    ax1.set_title("Distribuzione Generale dei Gradi", fontweight="bold")
    ax1.set_xlabel("Grado")
    ax1.set_ylabel("Frequenza")
    ax1.set_yscale('log')
    ax1.set_xscale('log')
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    # --- 5. PLOT 2 (SOTTO): Linee continue + Aree colorate (Core vs Periphery) ---
    # Usiamo i colori definiti nella tua funzione plot_core_vs_periphery
    
    # Core (Rosso)
    ax2.plot(bin_centers_s, y_core_s, color='#E63946', linewidth=2.5, label='Core')
    ax2.fill_between(bin_centers_s, y_core_s, color='#E63946', alpha=0.4)

    # Periphery (Blu)
    ax2.plot(bin_centers_s, y_peri_s, color='#1E6091', linewidth=2.5, label='Periphery')
    ax2.fill_between(bin_centers_s, y_peri_s, color='#1E6091', alpha=0.4)

    ax2.set_title("Distribuzione dei Gradi: Core vs Periferia", fontweight="bold")
    ax2.set_xlabel("Grado")
    ax2.set_ylabel("Frequenza")
    ax2.legend()
    ax2.grid(axis='y', linestyle='--', alpha=0.5)
    
    # --- 6. SALVATAGGIO ---
    plt.tight_layout()
    if save:
        out_deg = visual_dir / f"degree_distributions.png"
        fig.savefig(out_deg, dpi=300, bbox_inches="tight")
        print(f"✓ Salvato: {out_deg}")
    else:
        plt.show()
    plt.close(fig)
    return