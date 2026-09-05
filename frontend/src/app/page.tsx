export default function Home() {
  return (
    <main style={{ padding: "3rem", fontFamily: "system-ui, sans-serif", maxWidth: 720 }}>
      <h1>BridgeFlow AI</h1>
      <p>
        Four departmental spreadsheets in, one aligned Master Table out — with risk
        warnings and a quote recommendation.
      </p>
      <p style={{ opacity: 0.7 }}>
        Screens to build: Upload &amp; Sanitize → Resolve → Master Table &amp; Risks →
        Quote Simulator. See <code>docs/02-architecture.md</code>.
      </p>
    </main>
  );
}
