import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";

cytoscape.use(coseBilkent);

// Color coding per entity type — kept consistent with the NETRA PPT palette.
const NODE_COLORS = {
  Person: "#0070C0",
  Phone: "#0B2A4A",
  Account: "#1E7A3C",
  Vehicle: "#C9700E",
  Case: "#B03A2E",
};

// Risk-level colors override the default Person blue once a node has been
// scored (see risk.py / POST /risk/precompute and GET /risk/{id}).
const RISK_COLORS = {
  High: "#C0392B",
  Medium: "#E8A33D",
  Low: "#2E8B57",
};

function toElements(nodes, edges, highlightIds = []) {
  const nodeEls = nodes.map((n) => ({
    data: {
      id: n.id,
      label: n.display,
      type: n.type,
      personId: n.properties?.person_id,
      riskScore: n.properties?.risk_score,
      riskLevel: n.properties?.risk_level,
      // Full property bag, for the node-detail sidebar — works for any
      // entity type (Person, Phone, Account, Vehicle, Case), not just risk.
      properties: n.properties || {},
    },
    classes: highlightIds.includes(n.properties?.person_id) ? "flagged" : "",
  }));

  const edgeEls = edges.map((e) => ({
    data: {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.type,
    },
  }));

  return [...nodeEls, ...edgeEls];
}

export default function GraphView({ nodes, edges, highlightIds = [], onNodeClick }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(nodes, edges, highlightIds),
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele) => NODE_COLORS[ele.data("type")] || "#888",
            label: "data(label)",
            color: "#1a1a1a",
            "font-size": 9,
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: 28,
            height: 28,
            "border-width": 0,
          },
        },
        {
          // Overrides the default Person blue once a node carries a
          // risk_level property (set by POST /risk/precompute or
          // GET /risk/{id}). Unscored nodes keep the plain type color above.
          selector: 'node[riskLevel]',
          style: {
            "background-color": (ele) => RISK_COLORS[ele.data("riskLevel")] || NODE_COLORS.Person,
          },
        },
        {
          selector: "node.flagged",
          style: {
            "border-width": 3,
            "border-color": "#FFC000",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#B8C4D0",
            "curve-style": "bezier",
            "target-arrow-shape": "none",
            label: "data(label)",
            "font-size": 7,
            color: "#6b7280",
          },
        },
      ],
      layout: {
        name: "cose-bilkent",
        animate: true,
        nodeRepulsion: 6000,
        idealEdgeLength: 90,
      },
    });

    if (onNodeClick) {
      cy.on("tap", "node", (evt) => {
        onNodeClick(evt.target.data());
      });
    }

    cyRef.current = cy;
    return () => cy.destroy();
  }, [nodes, edges, highlightIds]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        background: "#ffffff",
        borderRadius: 8,
      }}
    />
  );
}
