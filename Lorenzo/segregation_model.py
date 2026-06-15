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
    """Updates the graph with a step of the segragation model
    Return: the number of links changed"""
    if labels is None:
        labels = tuple(G.vs['group'])
    if nodes is None:
        nodes = nodes_all(G)
    node_neighbors = G.neighbors(node)
    all_nodes_perm = np.random.permutation(nodes)
    # cerco A, vicino, ma diverso
    for candidateA in np.random.permutation(node_neighbors):
        if labels[node] != labels[candidateA]:
            A_neighbors = G.neighbors(candidateA)
            # cerco B, non vicino, ma simile
            for candidateB in all_nodes_perm:
                if labels[candidateB] == labels[node] and candidateB not in node_neighbors and candidateB != node:
                    # cerco C, non vicino di A, con cui sostituirmi
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

def segregation_sim(G: ig.Graph, satisfaction_treshold: float=0.5, max_step=1000, seed=42) -> Generator[ig.Graph]:
    """Segregation model for networks
    Return: a graph for each step"""
    np.random.seed(seed)
    G_sim = G.copy()
    nodes = nodes_all(G_sim)
    G_sim.rewire(n=100*G.ecount(), allowed_edge_types="simple")
    yield G_sim
    labels = tuple(G.vs['group'])
    # assumo che gli indici siano distribuiti da 0 a N: numero nodi
    nodes_failures = np.zeros_like(nodes, dtype=int)
    # iterazioni su tutta la rete
    for i_step in range(max_step):
        # singola iterazione sulla rete in ordine random
        rewires = 0
        nodes_changed = 0
        for node in np.random.permutation(nodes):
            if satisfaction(node, G_sim.neighbors(node), labels) < satisfaction_treshold:
                rewired_step = segregation_step(G_sim, node, labels=labels, nodes=nodes)
                rewires += rewired_step
                if not rewired_step:
                    nodes_failures[node] += 1
                else:
                    nodes_changed += 1

        print(f'Segregation Model Step {i_step+1}')
        print(f'Changed {nodes_changed} nodes with {rewires} rewires')
        print('')
        yield G_sim
        if not nodes_changed:
            print('Simulation ended in a stable configuration at step', i_step+1)
            print('Total failures', nodes_failures[nodes_failures>0].size)
            break
    return G_sim
