import igraph as ig
import numpy as np
from typing import Generator
from lorenzo_utils import *

def satisfaction(node: int, neighbors: list, labels: tuple) -> float:
    """Computes the satisfaction of a node with neighbors
    Return: the satisfaction fraction [0,1]"""
    assert len(neighbors) != 0, f"Node {node} has no neighbors :("

    return sum([labels[n] == labels[node] for n in neighbors]) / len(neighbors) 

def segregation_step(G: ig.Graph, node: int, labels: tuple=None, nodes=None) -> int:
    """Updates the graph with a step of the segragation model, per un singolo nodo
    Return: the number of links changed"""
    if labels is None:
        labels = tuple(G.vs['group'])
    if nodes is None:
        nodes = nodes_all(G) # [0, 1, 2,...]
    node_neighbors = G.neighbors(node)
    all_nodes_perm = np.random.permutation(nodes)
    # cerco A, vicino, ma diverso
    for candidateA in np.random.permutation(node_neighbors):
        if labels[node] != labels[candidateA]:
            A_neighbors = G.neighbors(candidateA)
            # cerco B, non vicino, ma simile
            for candidateB in all_nodes_perm:
                if labels[candidateB] == labels[node] and candidateB not in node_neighbors and candidateB != node:
                    # cerco C, non vicino di A, ma vicino di B con cui sostituirmi
                    for candidateC in np.random.permutation(G.neighbors(candidateB)):
                        if candidateC not in A_neighbors and candidateC != candidateA:
                            # perform the step by changing:
                            # (node,A) (B,C) -> (node,B) (A,C)
                            eid_node_A = G.get_eid(node, candidateA, directed=False, error=False)
                            eid_B_C = G.get_eid(candidateB, candidateC, directed=False, error=False)
                            G.delete_edges([eid_node_A,eid_B_C])
                            G.add_edges([(node, candidateB), (candidateA, candidateC)])
                            return 1
    return 0

def segregation_sim(G: ig.Graph, satisfaction_treshold: float=0.5, max_step=1000, 
                    seed=42, max_satisfaction=0.95) -> Generator[ig.Graph]:
    """Segregation model for networks
    Return: a graph for each step"""
    np.random.seed(seed)
    G_sim = G.copy()
    # assumo che gli indici siano distribuiti da 0 a N-1: N numero nodi
    nodes = nodes_all(G_sim)
    # la simulazione inizia da una configurazione random, che mantiene la distribuzione di grado originale
    G_sim.rewire(n=100*G.ecount(), allowed_edge_types="simple")
    labels = tuple(G.vs['group'])
    nodes_satisfaction = np.array([satisfaction(n,G_sim.neighbors(n),labels) for n in nodes])
    result_statistics = {
        'nodes_changed_step': 0,
        'nodes_failures_step': 0,
        'i_step': 0,
        'rewires_step': 0,
        'nodes_failures': tuple([0]*nodes.size),
        # satisfaction and segregation after rewire
        'segregation_index': np.mean(nodes_satisfaction),
        'satisfaction_rate': nodes_satisfaction[nodes_satisfaction >= satisfaction_treshold].size / nodes.size
    }
    nodes_failures = np.zeros_like(nodes, dtype=int)
    yield G_sim, dict(**result_statistics)
    # iterazioni su tutta la rete
    for i_step in range(max_step):
        # singola iterazione sulla rete in ordine random
        result_statistics['i_step'] = i_step+1
        result_statistics['nodes_failures_step'] = 0
        result_statistics['rewires_step'] = 0
        result_statistics['nodes_changed_step'] = 0
        for node in np.random.permutation(nodes):
            
            nodes_satisfaction[node] = satisfaction(node, G_sim.neighbors(node), labels)
            if nodes_satisfaction[node] < satisfaction_treshold:
                rewired_node = segregation_step(G_sim, node, labels=labels, nodes=nodes)
                result_statistics['rewires_step'] += rewired_node
                if not rewired_node:
                    nodes_failures[node] += 1
                    result_statistics['nodes_failures_step'] += 1
                else:
                    result_statistics['nodes_changed_step'] += 1

        result_statistics['satisfaction_rate'] = nodes_satisfaction[nodes_satisfaction >= satisfaction_treshold].size / nodes.size
        result_statistics['segregation_index'] = np.mean(nodes_satisfaction)
        result_statistics['nodes_failures'] = tuple(nodes_failures)
        
        if result_statistics['nodes_changed_step'] and result_statistics['satisfaction_rate'] < max_satisfaction:
            yield G_sim, dict(**result_statistics)
        else:
            break
    return G_sim, dict(**result_statistics)
