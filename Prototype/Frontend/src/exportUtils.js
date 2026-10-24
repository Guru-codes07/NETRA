/**
 * exportUtils.js — client-side CSV and PDF export for the currently
 * loaded graph. No backend calls, no extra npm dependencies: CSV is a
 * plain Blob download, PDF export opens a printable report in a new
 * tab and triggers the browser's native print-to-PDF dialog.
 */

function downloadBlob(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function csvEscape(value) {
  const str = value === null || value === undefined ? "" : String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/** Exports the currently loaded graph's nodes as a CSV file. */
export function exportNodesAsCSV(nodes) {
  const headers = ["id", "type", "label", "risk_score", "risk_level"];
  const rows = nodes.map((n) => [
    n.id,
    n.type,
    n.display,
    n.properties?.risk_score ?? "",
    n.properties?.risk_level ?? "",
  ]);

  const csv = [headers, ...rows]
    .map((row) => row.map(csvEscape).join(","))
    .join("\n");

  downloadBlob(`netra-graph-export-${Date.now()}.csv`, csv, "text/csv");
}

/**
 * Opens a printable, styled report (current graph summary + top risk
 * entries) in a new tab and triggers the browser's print dialog, where
 * the person can choose "Save as PDF". Avoids pulling in a PDF library
 * just for this.
 */
export function exportReportAsPDF(nodes, riskSummary, title = "NETRA Network Report") {
  const personNodes = nodes.filter((n) => n.type === "Person");

  const riskRows = riskSummary?.top_5_highest_risk?.length
    ? riskSummary.top_5_highest_risk
    : personNodes
        .filter((n) => n.properties?.risk_score != null)
        .map((n) => ({
          name: n.display,
          person_id: n.properties.person_id,
          risk_score: n.properties.risk_score,
          risk_level: n.properties.risk_level,
        }));

  const win = window.open("", "_blank");
  if (!win) return; // popup blocked

  win.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${title}</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 32px; color: #1a1a1a; }
        h1 { font-size: 20px; margin-bottom: 4px; }
        .meta { color: #666; font-size: 12px; margin-bottom: 24px; }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #e0e0e0; font-size: 13px; }
        th { background: #f4f6f8; }
        .risk-High { color: #C0392B; font-weight: bold; }
        .risk-Medium { color: #B9770E; font-weight: bold; }
        .risk-Low { color: #1E7A3C; font-weight: bold; }
        .disclaimer { margin-top: 32px; font-size: 11px; color: #888; border-top: 1px solid #e0e0e0; padding-top: 12px; }
      </style>
    </head>
    <body>
      <h1>${title}</h1>
      <div class="meta">Generated ${new Date().toLocaleString()} · ${personNodes.length} people in current view</div>

      <h3>Risk Summary</h3>
      ${
        riskRows.length
          ? `<table>
              <tr><th>Name</th><th>Person ID</th><th>Risk Level</th><th>Score</th></tr>
              ${riskRows
                .map(
                  (r) => `<tr>
                    <td>${r.name}</td>
                    <td>${r.person_id}</td>
                    <td class="risk-${r.risk_level}">${r.risk_level}</td>
                    <td>${r.risk_score}/100</td>
                  </tr>`
                )
                .join("")}
            </table>`
          : `<p>No risk scores computed yet for this view. Run "Compute Risk Scores" first for a fuller report.</p>`
      }

      <h3>All People in Current View</h3>
      <table>
        <tr><th>Name</th><th>Person ID</th></tr>
        ${personNodes
          .map((n) => `<tr><td>${n.display}</td><td>${n.properties?.person_id ?? ""}</td></tr>`)
          .join("")}
      </table>

      <div class="disclaimer">
        NETRA is an investigative decision-support prototype over synthetic data.
        Risk scores are a structural heuristic, not a trained prediction model,
        and do not determine guilt. For investigator review only.
      </div>
    </body>
    </html>
  `);
  win.document.close();
  win.focus();
  win.print();
}
