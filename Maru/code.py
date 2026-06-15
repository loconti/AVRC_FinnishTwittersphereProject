def log_likelihood_score(G: ig.Graph, partition: np.ndarray, q: int, degree_corrected: bool=True):

    degree = np.array(G.vs['degree'])

    # matrice di mixing -> conteggio degli archi tra gruppi (Lrs)
    L, _ = mixing_matrix(G, partition=partition, normalized=False)

    # kr somma dei gradi di tutti i nodi nel gruppo r
    k = np.zeros(q)
    for i, r in enumerate(partition):
        k[r] += degree[i]

    # per SBM non-DC il denominatore è il numero di nodi per blocco, non la somma dei gradi
    n_r = np.bincount(partition, minlength=q).astype(float)
    denom = k if degree_corrected else n_r

    # log-likelihood
    log_likelihood = 0
    for r in range(q):
        for s in range(q):
            if L[r, s] > 0 and denom[r] > 0 and denom[s] > 0:
                log_likelihood += L[r][s] * np.log( L[r][s] / (denom[r] * denom[s]) )

    if degree_corrected:
        correction = np.sum(degree[degree > 0] * np.log(degree[degree > 0]))
        log_likelihood -= correction

    return log_likelihood, L, k
    
def count_edges_to_blocks(i: int, partition: np.ndarray, q: int,
                           adjacency: list) -> np.ndarray:
    
    m = np.zeros(q, dtype=int)
    for nb in adjacency[i]: # scorro sui vicini del nodo i
        m[partition[nb]] += 1
    return m

def delta_log_likelihood(i: int, old_block: int,
                         new_block: int,
                         L: np.ndarray,
                         k: np.ndarray,
                         m: np.ndarray,
                         degree: np.ndarray,
                         q: int,
                         block_sizes: np.ndarray,
                         degree_corrected: bool = True
                         ) -> float:
    """
    Calcola ΔLL = LL_new - LL_old quando il nodo i si sposta da old_block a new_block.

    Parametri
    ---------
    m      : count_edges_to_blocks(i, partition, q, adjacency)
    degree : array dei gradi di tutti i nodi
    """
    # non svuotare mai un blocco
    if block_sizes[old_block] <= 1:
        return -np.inf

    r, s = old_block, new_block
    ki = degree[i]

    # --- Costruisci L' localmente ------------------------------------------
    L_new = L.copy()
    L_new[r, r] -= m[r]
    L_new[s, s] += m[s]
    L_new[r, s] += m[r] - m[s]
    L_new[s, r] = L_new[r, s]
    # Aggiornamento archi verso tutti gli altri blocchi t
    for t in range(q):
        if t != r and t != s:
            L_new[r, t] -= m[t]
            L_new[t, r] -= m[t]
            L_new[s, t] += m[t]
            L_new[t, s] += m[t]

    # denominatore: gradi (DC-SBM) o conteggio nodi (SBM)
    if degree_corrected:
        d_new = k.copy()
        d_new[r] -= ki
        d_new[s] += ki
        d_old = k
    else:
        d_new = block_sizes.copy().astype(float)
        d_new[r] -= 1
        d_new[s] += 1
        d_old = block_sizes.astype(float)

    # --- Somma solo le righe r e s (cattura anche i termini simmetrici) ----
    def row_contrib(L_mat, d_vec, row):
        total = 0.0
        for t in range(q):
            if L_mat[row, t] > 0 and d_vec[row] > 0 and d_vec[t] > 0:
                total += L_mat[row, t] * np.log(L_mat[row, t] /
                                                 (d_vec[row] * d_vec[t]))
        return total

    delta = 0.0
    for row in (r, s):
        delta += row_contrib(L_new, d_new, row) - row_contrib(L, d_old, row)

    return delta
def fit_sbm(G: ig.Graph, partition: np.ndarray, q: int, max_iter: int = 100, seed: int = None, degree_corrected: bool = True):
    """
    Fitta uno Stochastic Block Model seguendo l'algoritmo greedy:
      1. Inizializzazione casuale
      2. Per ogni nodo in ordine random: sposta nel blocco che massimizza Δℓ
      3. Ripeti finché nessun miglioramento
 
    Returns
    -------
    partition     : np.ndarray  assegnazione finale dei nodi ai blocchi
    log_lik       : float       log-likelihood finale
    """
    if seed is not None:
        np.random.seed(seed)
 
    n = G.vcount()
    degree = np.array(G.vs['degree'])
 
    # Lista di adiacenza come array numpy 
    adjacency = [np.array(G.neighbors(i)) for i in range(n)]
    block_size = np.bincount(partition, minlength=q)
 
    # --- 1. Inizializzazione ------------------------------------------------
    
    ll, L, k = log_likelihood_score(G, partition, q, degree_corrected)
    print(f"[init] log-likelihood Degree-Corrected={degree_corrected} = {ll:.4f}")
 
    # --- 2. Ottimizzazione --------------------------------------------------
    for iteration in range(max_iter):
        improved = False
        order = np.random.permutation(n)
        m_moved = 0
        for i in order:
            old_block = partition[i]
 
            # Conta gli archi di i verso ogni blocco  (O(deg(i)))
            m = count_edges_to_blocks(i, partition, q, adjacency)
 
            best_delta = 0.0
            best_block = old_block
 
            for new_block in range(q):
                if new_block == old_block:
                    continue
                if block_size[old_block] <=1:
                    continue
 
                # FIX CRITICO: calcolo incrementale, nessuna copia di partition
                d = delta_log_likelihood(i, old_block, new_block,
                                         L, k, m, degree, q, block_size,
                                         degree_corrected)
                if d > best_delta:
                    best_delta = d
                    best_block = new_block
 
            # Applica lo spostamento solo se c'è un miglioramento reale
            if best_block != old_block:
                m_moved += 1
                block_size[old_block] -= 1
                block_size[best_block] += 1
                # Aggiorna L e k in-place  (O(q))
                r, s = old_block, best_block
                ki = degree[i]
                L[r, r] -= m[r]
                L[s, s] += m[s]
                L[r, s] += m[r] - m[s]
                L[s, r] = L[r, s]  # maintain symmetry (was a no-op)
                for t in range(q):
                    if t != r and t != s:
                        L[r, t] -= m[t]
                        L[t, r] -= m[t]
                        L[s, t] += m[t]
                        L[t, s] += m[t]
                k[r] -= ki
                k[s] += ki
                partition[i] = best_block      # FIX: aggiorna solo dopo la scelta
                improved = True
 
        ll_new, _, _ = log_likelihood_score(G, partition, q, degree_corrected)
        print(f"[iter {iteration+1}] nodi spostati: {m_moved}/{n}  "
      f"log-likelihood = {ll_new:.4f}  (Δ = {ll_new - ll:+.4f})")
        ll = ll_new
 
        if not improved:
            print(f"Convergenza raggiunta all'iterazione {iteration+1}.")
            break
        
    
    return partition, ll
def multiple_restart(G: ig.Graph, K: int = 2, n_restarts: int = 10, degree_corrected: bool = True):
    
    n = G.vcount()
    best_ll = -np.inf
    best_partition = None

    if degree_corrected:
        print("Fit della rete reale con Degree Corrected Stochastic Block Model")
    else:
        print("Fit della rete reale con Stochastic Block Model")    
    
    
    for restart in range(n_restarts):
        print(f"\n--- Restart {restart+1}/{n_restarts} ---")
        
        partition = np.random.randint(0, K, size=n)
        partition, ll = fit_sbm(G, partition=partition, q=K, max_iter=50, seed=restart, degree_corrected=degree_corrected)
        
        print(f"  log-likelihood finale: {ll:.4f}")
        
        if ll > best_ll:
            best_ll = ll
            best_partition = partition.copy()
    
    print(f"\n=== Miglior log-likelihood: {best_ll:.4f} ===")
    return best_partition, best_ll
final_partition, best_log_likelihood = multiple_restart(G, n_restarts=50, degree_corrected=False)