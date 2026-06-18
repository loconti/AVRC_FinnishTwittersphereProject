"""
export_simulation.py
--------------------
Esegue la simulazione di segregazione e salva i dati in `simulation_data.json`
da caricare nella visualizzazione HTML.

Uso:
    python export_simulation.py

Dipendenze: igraph, numpy, segregation_model, lorenzo_utils
"""

import json
import numpy as np
import igraph as ig
from segregation_model import segregation_sim, satisfaction, nodes_all, ei_index, cross_type_fraction
from lorenzo_utils import load_graph, DATA_DIR

# ── parametri ──────────────────────────────────────────────────────────────
GRAPH_FILE      = DATA_DIR + "immigration_23.graphml"   # cambia con il tuo file
THRESHOLD       = 0.5
MAX_STEP        = 1000
SAMPLE_NODES    = 300   # nodi da mostrare nel grafo visivo (troppi → lento)
SAMPLE_SEED     = 0
# ───────────────────────────────────────────────────────────────────────────

print("Carico il grafo...")
G = load_graph(GRAPH_FILE)
labels_arr = np.array([1 if v == "A" else 0 for v in G.vs["group"]])
nodes      = nodes_all(G)

# metriche sul grafo osservato reale (linea target)
attr_map_obs = {i: labels_arr[i] for i in range(G.vcount())}
ei_obs       = ei_index(G, attr_map_obs)
cross_obs    = cross_type_fraction(G, attr_map_obs)
sat_obs      = np.mean([satisfaction(n, G.neighbors(n), G.vs["group"]) for n in nodes])

print(f"Grafo osservato  →  EI={ei_obs:.3f}  cross={cross_obs:.3f}  sat={sat_obs:.3f}")

# ── campione fisso di nodi per la visualizzazione visiva ──────────────────
rng = np.random.default_rng(SAMPLE_SEED)
# campiona bilanciando le due community
idx_A = np.where(labels_arr == 1)[0]
idx_B = np.where(labels_arr == 0)[0]
half  = SAMPLE_NODES // 2
sample_idx = np.concatenate([
    rng.choice(idx_A, size=min(half, len(idx_A)), replace=False),
    rng.choice(idx_B, size=min(half, len(idx_B)), replace=False),
])
sample_set = set(sample_idx.tolist())
# mappa indice originale → indice nel campione
orig_to_sample = {orig: i for i, orig in enumerate(sample_idx)}

def extract_sample_edges(graph, sample_set, orig_to_sample):
    """Restituisce gli archi tra i nodi del campione."""
    edges = []
    for e in graph.es:
        u, v = e.source, e.target
        if u in sample_set and v in sample_set:
            edges.append([orig_to_sample[u], orig_to_sample[v]])
    return edges

# nodi del campione (label fissa per tutta la simulazione)
sample_nodes = [
    {"id": orig_to_sample[i], "group": int(labels_arr[i])}
    for i in sample_idx
]

# ── simulazione ────────────────────────────────────────────────────────────
print(f"\nSimulazione avviata  (threshold={THRESHOLD})...")
snapshots  = []
ei_series  = []
cross_series = []
sat_series = []

for step_idx, (G_step, stats) in enumerate(
    segregation_sim(G, satisfaction_treshold=THRESHOLD, max_step=MAX_STEP)
):
    step_num = stats["i_step"]
    ei_val   = stats["segregation_index"]   # mean satisfaction ≈ segregation
    sat_val  = stats["satisfaction_rate"]

    # ricalcola EI e cross fraction (più precisi) ogni N step per non rallentare troppo
    if step_idx % 5 == 0 or step_idx == 0:
        lbl_tuple = tuple(G_step.vs["group"])
        attr_map  = {i: (1 if lbl_tuple[i] == "A" else 0) for i in range(G_step.vcount())}
        ei_real   = ei_index(G_step, attr_map)
        cross_real = cross_type_fraction(G_step, attr_map)
    else:
        ei_real    = ei_series[-1]["ei"] if ei_series else 0
        cross_real = cross_series[-1] if cross_series else 0

    ei_series.append({"step": step_num, "ei": round(ei_real, 4)})
    cross_series.append(round(cross_real, 4))
    sat_series.append(round(sat_val, 4))

    # salva snapshot visivo solo ogni 5 step (riduce dimensione file)
    if step_idx % 5 == 0:
        snap_edges = extract_sample_edges(G_step, sample_set, orig_to_sample)
        snapshots.append({
            "step":  step_num,
            "edges": snap_edges,
        })

    print(f"  Step {step_num:3d}  EI={ei_real:.3f}  sat={sat_val:.3f}  "
          f"rewires={stats['rewires_step']}")

print(f"\nSimulazione terminata: {len(ei_series)} step registrati, "
      f"{len(snapshots)} snapshot visivi")

# ── assembla e salva JSON ─────────────────────────────────────────────────
output = {
    "meta": {
        "threshold":   THRESHOLD,
        "n_nodes_full": G.vcount(),
        "n_edges_full": G.ecount(),
        "sample_size":  len(sample_nodes),
        "ei_observed":  round(ei_obs, 4),
        "cross_observed": round(cross_obs, 4),
        "sat_observed": round(float(sat_obs), 4),
    },
    "nodes": sample_nodes,         # lista fissa per tutta la sim
    "snapshots": snapshots,        # archi del campione per ogni snapshot
    "metrics": {                   # serie temporali su tutta la rete
        "ei":    ei_series,
        "cross": cross_series,
        "sat":   sat_series,
    },
}

with open("simulation_data.json", "w") as f:
    json.dump(output, f, separators=(",", ":"))

print("✓  Salvato  simulation_data.json")
print(f"   Dimensione file: {__import__('os').path.getsize('simulation_data.json') / 1024:.1f} KB")
