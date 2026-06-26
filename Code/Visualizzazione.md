# Visualizzazione dinamica del grafo
Questa visualizzazione è stata pensata per visulizzare diversi fenomeni che sono emersi nella nostra analisi.

Innanzitutto abbiamo permesso la visualizzazione di due reti: una che riguarda il topic immigrazione nell'anno 19 e una nell'anno 2023. Mettendo di default la rete che abbiamo selezionato per l'analisi, ovvero quella del 2023. La scelta avviene tramite un menù a tendina.


## Layout
Abbiamo deciso di costruire il layout in base alle comunità, ovvero di separare le due comunità disponendole ai due estremi di un cerchio. Inoltre, abbiamo impostato la forza repulsiva con cui si dispongono i nodi in funzione del loro grado (maggiore per nodi ad alto grado, minore per nodi a basso grado). Abbiamo impostato le seguenti forze:

- *link*: impostazione della forza attrattiva dei link
- *charge*: impostazione della forza repulsiva in funzione del grado
- *center*: impostazione della forza verso il centro di massa del layout
- *xCluster/yCluster*: impostazione delle coordinate x e y per la divisione del layout in base alle comunità

 



```js
// Avvio della simulazione
simulation = d3.forceSimulation(currentNodes)
                .force("link", d3.forceLink(currentLinks).id(d => d.id).distance(2).strength(0.3)) 
                .force("charge", d3.forceManyBody().strength(d => chargeScale(d.degree)).theta(0.9)) 
                .force("center", d3.forceCenter(width / 2, height / 2))  
                .force("xCluster", d3.forceX(d => tgt.get(d.group).x).strength(0.08))  
                .force("yCluster", d3.forceY(d => tgt.get(d.group).y).strength(0.08)) 
                .alphaDecay(0.05)
                .velocityDecay(0.4)
                .on("tick", draw)
                .on("end", () => console.log("Simulazione stabilizzata,", currentNodes.length, "nodi visibili"));
```

## Misure di centralità
1. Abbiamo implementato uno slider per selezionare diversi valori di coreness per cui visualizzare la rete, da 0 (valore per cui si visualizza la rete interamente) al valore massimo che si assesta a 25.

2. Abbiamo aggiunto un menù a tendina per porre la dimensione dei nodi in funzione di diverse misure di centralità: degree, eigenvector centrality, betweenness centrality.



## Layout dei nodi
Abbiamo evidenziato (mediante il bordo dorato) i top nodi in base alla centralità selezionata tramite il menù a tendina. Il numero di top nodi può essere variato tramite uno slider da 10 a 100 con passo di 10, avendo come valore di default 20.



## Hovering
Inoltre, abbiamo implementato la possibilità di puntanre un nodo con il cursore in maniera che rimanga visibile il nodo, i nodi appartenenti alla sua neighborhood e i link che li collegano.

## Zoom 
 Nella nostra visualizzazione è possibile ingrandire la rete lasciando invariata la dimensione dei nodi così da ridurre l'overlap dei nodi dovuta alla grande dimensione della rete.

               
