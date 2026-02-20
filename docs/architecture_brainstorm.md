# Weak Signal Intelligence - Architecture Brainstorming

## Goal
Transform the system from a simple "keyword-checker" into an intelligent engine that can:
1.  Extract internal/external signals from *any* dataset.
2.  Interpret conclusions (The "So What?").
3.  Identify impacts and possibilities (The "What If?").
4.  Trace chain reactions ("Why Chains").

---

## Approach 1: The AI-Powered Analyst (Recommended)
This approach integrates a Large Language Model (LLM) like GPT-4, Gemini, or a local Llama model (via Ollama) to act as the reasoning engine.

### Workflow
1.  **Data Ingestion (Python)**: 
    *   Upload CSV.
    *   Calculate statistical facts: "Sales dropped 5% in Q3", "Inventory spiked 20% in Nov".
2.  **Context Construction**:
    *   System creates a text summary: *"I have a dataset for the [Industry] sector. Over the last 3 months, [Metric A] is up 10% while [Metric B] is down 5%."*
3.  **AI Interpretation (LLM API)**:
    *   Send prompt to AI: *"Analyze these trends. What are likely external drivers (e.g., geopolitical, seasonal)? What are the valid business impacts? Generating a 'Why Chain' of possibilities."*
4.  **Output**:
    *   AI returns JSON with:
        *   **Signal**: "Potential Supply Chain Disruption"
        *   **Confidence**: High
        *   **Why Chain**: "Cost Up -> Margin Compression -> Price Increase -> Demand Drop"

### Pros
*   **Instant "Intelligence"**: Can deduce that "Urea" implies "Agriculture" implies "Monsoon dependency" without us coding it.
*   **Flexible**: Works for unknown datasets immediately.
*   **Deep Insights**: Can generate natural language explanations of impacts.

### Cons
*   **Cost/Privacy**: Requires sending non-sensitive data stats to an API.

---

## Approach 2: The "Persona" Rule & Ontology Engine
This approach builds a library of static knowledge files (Personas) that mapped specific industries to specific logic.

### Structure
Create a `personas/` folder:
*   `jewellery.json`
*   `ev_batteries.json`
*   `fertilizer.json`
*   `retail_clothing.json`

### Persona Definition (Example)
```json
{
  "industry": "Fertilizer",
  "keywords": ["urea", "dap", "sowing", "harvest"],
  "external_factors": ["Monsoon", "Gas Prices", "Import Policy"],
  "logic_chains": [
    {
      "trigger": "inventory > 20% increase",
      "conclusion": "Overstocking Risk",
      "possible_cause": "Weak Monsoon or Delayed Sowing",
      "impact": "Liquidity Crunch"
    }
  ]
}
```

### Workflow
1.  **Fingerprinting**: When CSV is uploaded, scan headers against persona keywords to identify Industry.
2.  **Rule Execution**: Load the matching JSON and run the specific `logic_chains`.
3.  **Fallback**: If no persona matches, use the Generic Statistical model (current implementation).

### Pros
*   **Deterministic**: You know exactly why a signal fired.
*   **Fast**: No API latency.
*   **Private**: Data stays local.

### Cons
*   **High Maintenance**: We must manually write a file for every industry.
*   **Limited "Reasoning"**: It can't guess relationships we haven't explicitly coded.

---

## Approach 3: The Hybrid Model (Ultimate)
Combine both for robustness.

1.  **System**: Tries to match a **Persona** first for high-precision, predefined signals.
2.  **AI Layer**: If the data is weird or the persona logic is insufficient, it sends the statistical summary to the **AI Agent** for a "second opinion" or "deep dive".
3.  **Real-time External Validation**: 
    *   If AI says "Monsoon might be weak", the system triggers a **Web Search** (Google News API/SerpAPI) for "India Monsoon Forecast 2025" to confirm the signal.

---

## Proposed Roadmap

### Phase 1: Persona Engine (Structured Foundations)
1.  Refactor `main.py` to move logic out of `if/else` blocks and into a `SignalEngine` class.
2.  Create a standardized `Persona` class that defines how to map columns to concepts (e.g., "urea" = "product", "inventory_tons" = "stock").

### Phase 2: AI Integration (The "Brain")
1.  Create an interface for an LLM (e.g., `LangChain` or direct API).
2.  Send *metadata only* (column names + trend summary) to the AI to generate the "Impact Analysis" text.

### Phase 3: The "Why Chain" Visualization
1.  Frontend visualization (Node Graph) showing:
    *   Signal (Start) -> Cause (Middle) -> Impact (End).
