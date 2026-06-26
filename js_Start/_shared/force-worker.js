// =============================================================================
// force-worker.js — runs a d3-force simulation off the main thread.
//
// Protocol (parent ↔ worker):
//   parent → worker: { type: "init", nodes, links, w, h }
//                    { type: "reheat", alpha }            // re-bump alpha
//                    { type: "drag-start", id, x, y }     // pin node to (x, y)
//                    { type: "drag-move",  id, x, y }
//                    { type: "drag-end",   id }
//                    { type: "stop" }
//   worker → parent: { type: "tick", positions: Float32Array }   // [x0, y0, x1, y1, …]
//                    { type: "links",  endpoints: Uint16Array }    // [s0, t0, s1, t1, …]
//                    { type: "end" }
//
// The worker re-imports d3 from the CDN. This is the same script used by every
// L11 demo, so the network/CDN cost is shared.
// =============================================================================

importScripts("https://d3js.org/d3.v7.min.js");

let sim = null;
let nodes = null;
let links = null;

self.onmessage = (event) => {
    const m = event.data;
    switch (m.type) {
        case "init": return init(m);
        case "reheat": return sim && sim.alpha(m.alpha ?? 0.5).restart();
        case "drag-start": return dragSet(m.id, m.x, m.y, true);
        case "drag-move":  return dragSet(m.id, m.x, m.y, false);
        case "drag-end":   return dragClear(m.id);
        case "stop": return sim && sim.stop();
    }
};

function init({ nodes: ns, links: ls, w, h }) {
    nodes = ns;
    links = ls;

    // post the (now numeric) link endpoints once so the renderer can draw
    // edges without having to look up nodes by id on every tick.
    const ep = new Uint16Array(links.length * 2);
    const idIndex = new Map(nodes.map((d, i) => [d.id, i]));
    for (let i = 0; i < links.length; i++) {
        ep[i * 2]     = idIndex.get(links[i].source);
        ep[i * 2 + 1] = idIndex.get(links[i].target);
    }
    self.postMessage({ type: "links", endpoints: ep.buffer }, [ep.buffer]);

    if (sim) sim.stop();
    sim = d3.forceSimulation(nodes)
        .force("link",   d3.forceLink(links).id(d => d.id).distance(20))
        .force("charge", d3.forceManyBody().strength(-30).theta(0.1))   // low theta = heavy compute
        .force("x",      d3.forceX(w / 2).strength(0.07))
        .force("y",      d3.forceY(h / 2).strength(0.07))
        .alphaDecay(0.02)
        .on("tick", () => {
            // pack positions into a Float32Array and ship via Transferable
            const pos = new Float32Array(nodes.length * 2);
            for (let i = 0; i < nodes.length; i++) {
                pos[i * 2]     = nodes[i].x;
                pos[i * 2 + 1] = nodes[i].y;
            }
            self.postMessage({ type: "tick", positions: pos.buffer }, [pos.buffer]);
        })
        .on("end", () => self.postMessage({ type: "end" }));
}

function dragSet(id, x, y, isStart) {
    if (!nodes) return;
    const n = nodes.find(d => d.id === id);
    if (!n) return;
    if (isStart) {
        if (sim) sim.alphaTarget(0.3).restart();
    }
    n.fx = x; n.fy = y;
}

function dragClear(id) {
    if (!nodes) return;
    const n = nodes.find(d => d.id === id);
    if (n) { n.fx = null; n.fy = null; }
    if (sim) sim.alphaTarget(0);
}
