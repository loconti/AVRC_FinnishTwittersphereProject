const CANVAS = {
    width: 800,
    margin: { top: 24, right: 30, bottom: 36, left: 50 }
};

// idOf — link source/target is a string id before d3.forceLink runs, a node
// object after; this unifies both.
const idOf = ref => ref.id ?? ref;

// buildNeighbors — Map<id, Set<id>> where each node id maps to itself plus
// every neighbour's id. O(1) lookup per hover event. (Technique introduced
// in 11c §2; this is the same construction packaged for reuse.)
function buildNeighbors(nodes, links) {
    const m = new Map(nodes.map(n => [n.id, new Set([n.id])]));
    for (const l of links) {
        const a = idOf(l.source), b = idOf(l.target);
        m.get(a).add(b); m.get(b).add(a);
    }
    return m;
}

// Every L11 demo uses a fixed 800-px coordinate space so simulations have the
// same scale across examples. CSS scales the rendered SVG to fit the page
// container via `width: 100%; height: auto;` declared in chart.css.
//
// Structure: <svg> > <g margin> > <g plot>. `plot` is the pan/zoom target.
// Every demo gets pan + zoom for free; pass opts.pan = false to disable.
function makeCanvas(selector, height, opts = {}) {
    const m = { ...CANVAS.margin, ...(opts.margin || {}) };
    const w = opts.width ?? CANVAS.width;
    const innerW = w - m.left - m.right;
    const innerH = height - m.top - m.bottom;

    const root = d3.select(selector).append("svg")
        .attr("width", w).attr("height", height)
        .attr("viewBox", `0 0 ${w} ${height}`)
        .attr("preserveAspectRatio", "xMidYMid meet")
        .style("background", "#fafafa").style("border", "1px solid #ddd")
        .style("display", "block").style("cursor", "grab")
        .style("touch-action", "none");

    const marginG = root.append("g")
        .attr("transform", `translate(${m.left}, ${m.top})`);
    if (opts.showPlotArea) {
        marginG.append("rect")
            .attr("width", innerW).attr("height", innerH)
            .attr("fill", "#f8f9fa").attr("stroke", "#dee2e6");
    }
    const plot = marginG.append("g");

    if (opts.pan !== false) {
        const zoom = d3.zoom()
            .scaleExtent([0.3, 4])
            .on("zoom",  (e) => plot.attr("transform", e.transform))
            .on("start", () => root.style("cursor", "grabbing"))
            .on("end",   () => root.style("cursor", "grab"));
        root.call(zoom);
        root.on("dblclick.zoom", null);
    }

    return { root, plot, marginG, innerW, innerH, margin: m, width: w, height };
}

// ---------------------------------------------------------------
// Categorical legend — one coloured square + label per entry in a
// d3 ordinal scale's domain, laid out as a centred horizontal row.
// HTML + flexbox so it wraps and centres at any container width.
//
// Usage: provide an empty <div> in the page; legend() fills it.
//
//     <div class="legend" id="legend-stack"></div>
//     <div class="container" id="demo-stack"></div>
//
//     legend("#legend-stack", colorScale);                 // default
//     legend("#legend-stack", colorScale, { size: 16 });   // bigger squares
// ---------------------------------------------------------------
function legend(selector, scale, opts = {}) {
    const size = opts.size ?? 14;
    const align = opts.align ?? "center";   // "start" | "center" | "end"
    const wrap = d3.select(selector)
        .style("display", "flex")
        .style("flex-wrap", "wrap")
        .style("justify-content", align)
        .style("gap", "0.4em 1.2em")
        .style("margin", "0.4em 0")
        .style("font-size", "var(--text-md)");
    wrap.selectAll("*").remove();   // idempotent on re-render
    scale.domain().forEach(d => {
        const item = wrap.append("span")
            .style("display", "inline-flex")
            .style("align-items", "center")
            .style("gap", "0.4em");
        item.append("span")
            .style("display", "inline-block")
            .style("width", size + "px").style("height", size + "px")
            .style("border-radius", "2px")
            .style("background", scale(d));
        item.append("span").text(d);
    });
    return wrap;
}

// ---------------------------------------------------------------
// Custom force: keeps nodes inside an axis-aligned rectangle.
// Pass the inner-canvas dimensions; the force clamps each tick.
// ---------------------------------------------------------------
function boundaryForce(innerW, innerH, pad = 4) {
    let nodes;
    function force() {
        for (const d of nodes) {
            const r = (d.__r ?? pad);
            d.x = Math.max(r,      Math.min(innerW - r, d.x));
            d.y = Math.max(r,      Math.min(innerH - r, d.y));
        }
    }
    force.initialize = _ => { nodes = _; };
    return force;
}

// ---------------------------------------------------------------
// Fit-to-canvas: lets a force simulation expand naturally (no
// boundary force), then on "end" computes the bounding box of the
// node positions and applies a single transform to a wrapping <g>
// so the graph fills the canvas.
//
//     const wrap = c.plot.append("g");
//     // marks (link, node, label) appended inside wrap
//     fitToCanvas(wrap, sim, nodes, c.innerW, c.innerH);
//
// The transform is recomputed on every "end" event, so the graph
// re-fits whenever the simulation reheats (drag, slider change, …).
// Strokes use vector-effect:non-scaling-stroke so they don't shrink
// with the layout — set that on the marks if you want constant width.
// ---------------------------------------------------------------
function fitToCanvas(wrap, sim, nodes, innerW, innerH, opts = {}) {
    const padding = opts.padding ?? 20;
    const dur = opts.duration ?? 400;
    function fit() {
        if (!nodes.length) return;
        const xs = nodes.map(d => d.x), ys = nodes.map(d => d.y);
        const x0 = d3.min(xs), x1 = d3.max(xs);
        const y0 = d3.min(ys), y1 = d3.max(ys);
        const dx = (x1 - x0) || 1;
        const dy = (y1 - y0) || 1;
        const k = Math.min(
            (innerW - 2 * padding) / dx,
            (innerH - 2 * padding) / dy
        );
        const tx = padding + (innerW - 2 * padding - k * dx) / 2 - k * x0;
        const ty = padding + (innerH - 2 * padding - k * dy) / 2 - k * y0;
        wrap.transition().duration(dur)
            .attr("transform", `translate(${tx}, ${ty}) scale(${k})`);
    }
    sim.on("end.fit", fit);
    return fit;
}

// ---------------------------------------------------------------
// "Warming up…" overlay over the SVG. Hides as soon as alpha drops
// below 0.1 (~1.7s at default decay) — the layout is visually
// settled by then even though the simulation keeps ticking down to
// alphaMin (0.001 ≈ 5s). Listening on tick lets us cut warmup time
// roughly in half compared with waiting for the "end" event.
// ---------------------------------------------------------------
function attachWarmup(svgRoot, sim, label = "warming up the layout…") {
    const w = +svgRoot.attr("width");
    const h = +svgRoot.attr("height");
    const overlay = svgRoot.append("g").attr("class", "warmup-overlay");
    overlay.append("rect")
        .attr("width", w).attr("height", h)
        .attr("fill", "white").attr("opacity", 0.7);
    overlay.append("text")
        .attr("x", w / 2).attr("y", h / 2)
        .attr("text-anchor", "middle")
        .style("font-size", "var(--text-md)")
        .style("fill", "#555")
        .text(label);

    const HIDE_AT = 0.1;
    function hide() {
        overlay.transition().duration(200).style("opacity", 0).remove();
        sim.on("tick.warmup", null);
        sim.on("end.warmup",  null);
    }
    sim.on("tick.warmup", () => { if (sim.alpha() <= HIDE_AT) hide(); });
    sim.on("end.warmup",  hide);
    return overlay;
}
