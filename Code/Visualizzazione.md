# Visualizzazione
Questa visualizzazione è stata pensata per mostrare le proprietà 

Innanzitutto abbiamo permesso la visualizzazione di due reti: una che riguarda il topic immigrazione nell'anno 19 e una nell'anno 2023. Mettendo di default la rete che abbiamo selezionato per l'analisi, ovvero quella del 2023.La scleta avviene tramite un menù a tendina.

```js

<label>Seleziona anno:</label>
    <select id="graph-select">
        <option value="grafo.json">2023</option> // file json contenente i dati della rete immigrazione 2023
        <option value="grafo19.json">2019</option> // file json contenente i dati della rete immigrazione 2019
    </select>
```

## Layout
Abbiamo deciso di costruire il layout in base alle comunità, ovvero di separare le due comunità disponendole ai due estremi di un cerchio. Inoltre, abbiamo impostato la forza repulsiva con cui si dispongono i nodi in funzione del loro grado (maggiore per nodi ad alto grado, minore per nodi a basso grado).

```js
//Calcolo delle costanti per il layout diviso per comunità
const cks = [...new Set(currentNodes.map(d => d.group))]; // trova le community
const ang = i => (i / cks.length) * 2 * Math.PI; // divide la circonferenza in base alla comunità
const rad = 0.30 * Math.min(innerWidth, innerHeight); // raggio della circonferenza su cui posiziono le comunità
const tgt = new Map(cks.map((cm, i) => [cm, { // coordinate del punto sulla circonferenza associate alla comunità
    x: innerWidth / 2 + rad * Math.cos(ang(i)),
    y: innerHeight / 2 + rad * Math.sin(ang(i))
}]));

//Calcolo delle costanti per l'impostazione della forza repulsiva
const maxDegree = d3.max(graph.nodes, d => d.degree) || 1;
const chargeScale = d3.scaleSqrt() 
    .domain([1, maxDegree])
    .range([-5, -40]); // periferia: -5 (debole) | core: -40 (forte) 
```


```js
// Avvio della simulazione
simulation = d3.forceSimulation(currentNodes)
                .force("link", d3.forceLink(currentLinks).id(d => d.id).distance(2).strength(0.3)) // impostazione dei link
                .force("charge", d3.forceManyBody().strength(d => chargeScale(d.degree)).theta(0.9)) // impostazione della forza repulsiva in funzione del grado
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("xCluster", d3.forceX(d => tgt.get(d.group).x).strength(0.08)) //dispozione della cordinata x per la divisione del layout in base alle comunità 
                .force("yCluster", d3.forceY(d => tgt.get(d.group).y).strength(0.08)) // dispozione della cordinata y per la divisione del layout in base alle comunità
                .alphaDecay(0.05)
                .velocityDecay(0.4)
                .on("tick", draw)
                .on("end", () => console.log("Simulazione stabilizzata,", currentNodes.length, "nodi visibili"));
```

## Misure di centralità
1. Abbiamo implementato uno slider per selezionare diversi valori di coreness per cui visualizzare la rete, da 0 (valore per cui si visualizza la rete interamente) al valore massimo che si assesta a 25.

```js
// Implementazione dello slider relativo alla coreness
<label>Coreness minima: <span id="coreness-value">0</span></label>
  <input type="range" id="coreness-slider" min="0" max="0" value="0" step="1">

// Inizializzazione dello slider in base alla coreness massima reale nei dati
const maxCoreness = d3.max(graph.nodes, d => d.coreness);
d3.select("#coreness-slider")
            .attr("max", maxCoreness)
            .on("input", function() {
                const value = +this.value;
                d3.select("#coreness-value").text(value);
                updateGraph(value);
            });

```

2. Abbiamo aggiunto un menù a tendina per porre la dimensione dei nodi in funzione di diverse misure di centralità: degree, eigenvector centrality, betweenness centrality.

```js
// Implementazione del menù a tendina relativo alle diverse misure di centralità
<label>Dimensione nodi in base a:</label>
    <select id="centrality-select">
        <option value="eigenvector">Eigenvector centrality</option>
        <option value="degree">Degree centrality</option>
        <option value="betweenness">Betweenness centrality</option>
        
    </select>

// Inizializzazione del menù a tendina relativo alla scelta della misura di centralità
        
d3.select("#centrality-select").property("value", "eigenvector");
        currentMetric = "eigenvector";
```



# Layout dei nodi
Abbiamo evidenziato (mediante il bordo dorato) i top nodi delle diverse centralità di un numero che può essere variato da 10 a 100 con passo di 10, avendo come valore di default 20.

```js
// Implementazione dello slider per la scelta del numero dei top nodes
let topNodesCount = 20;
<label>Top nodi da evidenziare: <span id="top-nodes-value">20</span></label>
    <input type="range" id="top-nodes-slider" min="10" max="100" value="20" step="10">

// Inizializzazione dello slider per la scelta del numero dei top nodes
d3.select("#top-nodes-slider").property("value", 20);
d3.select("#top-nodes-slider")
        .on("input", function() {
            topNodesCount = +this.value;
            });

```

# Hovering
Inoltre, abbiamo implementato la possibilità di avere l'hovering in modo che puntando un nodo con il cursore rimanga visibile il nodo, i nodi appartenenti alla sua neighborhood e i link che li collegano.


```js
// 1. Link

            currentLinks.forEach(d => {
                const sid = d.source.id ?? d.source;
                const tid = d.target.id ?? d.target;
                const active = !isHovering || 
                (neighborSet.has(sid) && neighborSet.has(tid));
                ctx.beginPath();
                if (isHovering) {  // il layout cambia in base all'attivazione dell'hovering
                    ctx.strokeStyle = active
                    ? "rgba(187, 187, 187, 0.7)"
                    : "rgba(187, 187, 187, 0.0)";

                } else {
                    ctx.strokeStyle = "rgba(187, 187, 187, 0.05)";
                }

                ctx.lineWidth = 0.5 / transform.k; // mantiene lo spessore costante mentre zoomi
                ctx.moveTo(d.source.x, d.source.y);
                ctx.lineTo(d.target.x, d.target.y);
                ctx.stroke();
            });

            // 2. Nodi
            currentNodes.forEach(d => {
                // disegno prima i non top nodi
                if (topNodes.has(d.id)) return; // salta i top nodi
                
                const r = (radiusScale(d[currentMetric] || 0)) / transform.k;
                
                const isNeighbor = neighborSet.has(d.id);
                //const isHovered = hoveredNode && d.id === hoveredNode.id;
                
                ctx.beginPath();
                ctx.arc(d.x, d.y, r, 0, 2 * Math.PI);
                ctx.globalAlpha = isHovering ? (isNeighbor ? 1 : 0.05) : 0.6; // il layout cambia in base all'attivazione dell'hovering
                ctx.strokeStyle = 'white';
                ctx.stroke()
                ctx.fillStyle = colorScale(d.group);
                ctx.fill();
            });

            // ora disegnamo i top nodi
            currentNodes.forEach(d => {
                if (!topNodes.has(d.id)) return; 
                const r = (radiusScale(d[currentMetric] || 0)) / transform.k;
                const isNeighbor = neighborSet.has(d.id);
                const isHovered = hoveredNode && d.id === hoveredNode.id;
                
                ctx.beginPath();
                ctx.arc(d.x, d.y, r, 0, 2 * Math.PI);
                ctx.globalAlpha = isHovering ? (isNeighbor ? 1 : 0.05) : 0.6;
                ctx.fillStyle = colorScale(d.group);
                ctx.fill();

                ctx.globalAlpha = isHovering && !isNeighbor ? 0.05 : 1;
                ctx.strokeStyle = '#FFD700';
                ctx.lineWidth = ( isHovered ? 3 : 1.5 ) / transform.k;
                ctx.stroke();
                        


            });



            ctx.restore();
        }


```