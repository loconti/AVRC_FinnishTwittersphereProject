import igraph as ig
import numpy as np
import matplotlib.pyplot as plt

# misure di centralità
DIR = '../Data/'
def load_graph(filename='climate_19.graphml') -> ig.Graph:
    return ig.Graph.Read_GraphML(DIR + filename)

G = load_graph()

degrees = G.degree()
bins = 7
fig, ax = plt.subplots(figsize=(12,6), layout='standard')
ax.hist(degrees, bins=bins, histtype='stepfilled', color='red', alpha=0.60, edgecolor='red', linewidth=2.0)