import { NextRequest, NextResponse } from "next/server";

const allowedGroups = new Set(["category", "product", "customer", "city", "month"]);
const allowedMetrics = new Set(["sales", "orders", "units", "average_order_value"]);
const allowedChartTypes = new Set(["bar", "line", "area", "scatter", "pie"]);

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const question = String(body.question || "").trim();
    const rows = Array.isArray(body.rows) ? body.rows.slice(0, 100) : [];
    const analysis = body.analysis && typeof body.analysis === "object" ? body.analysis : null;

    if (!question) return NextResponse.json({ error: "Enter a question first." }, { status: 400 });
    if (!analysis || !Number.isFinite(Number(analysis.records)) || Number(analysis.records) < 1) {
      return NextResponse.json({ error: "There are no records in the current filters. Choose All time or adjust the filters." }, { status: 400 });
    }

    const summary = {
      dataset: String(body.dataset || "Uploaded dataset"),
      scope: "Exact aggregates calculated across every record in the current dashboard filters. The rows array is only a small illustrative sample and must not be used to calculate totals or rankings.",
      records: Number(analysis.records),
      distinct_orders: Number(analysis.distinct_orders),
      distinct_customers: Number(analysis.distinct_customers),
      distinct_products: Number(analysis.distinct_products),
      total_sales: Number(analysis.total_sales),
      total_units: Number(analysis.total_units),
      total_cost: Number(analysis.total_cost),
      grouped_results: analysis.groups || {},
      sample_rows: rows
    };

    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      return NextResponse.json({
        error: "PULSE AI needs an OpenAI API key. Add OPENAI_API_KEY to web/.env.local, restart the app, and try again. Your question history will still be saved in this browser."
      }, { status: 503 });
    }

    const system = `You are PULSE, a careful business data analyst. Answer only from the supplied dataset context. The records, totals, distinct counts, and grouped_results are exact aggregates calculated across the entire current filtered dataset. Use grouped_results for rankings, city comparisons, product/category sales, and chart explanations. sample_rows is illustrative only: never use it to calculate totals, rankings, or unique counts. Never invent missing fields, values, causes, or business facts. Distinguish sales from profit; total_cost is only useful if meaningful cost values were supplied. If a requested metric cannot be computed, explain which field is missing. State the record count and current filter scope when useful. Return valid JSON only with this exact shape:
{"answer":"plain language response with specific numbers and caveats","insight":"plain-English explanation of the chart, the main pattern supported by the data, and a cautious business implication","chart":null}
If the user requests a chart, chart must be {"title":"short chart title","description":"what the chart shows and any limitation","chartType":"bar|line|area|scatter|pie","groupBy":"category|product|customer|city|month","metric":"sales|orders|units|average_order_value"}. Follow the requested chart type exactly when supported. Use line or area for trends over time, scatter for relationships (average product unit price on x and total units sold on y), and pie for composition with few groups. If no chart is requested, chart=null. Do not include markdown fences.`;

    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: process.env.OPENAI_MODEL || "gpt-4o-mini",
        temperature: 0.2,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: system },
          ...((Array.isArray(body.history) ? body.history : []).slice(-6).map((m: any) => ({
            role: m.role === "assistant" ? "assistant" : "user",
            content: String(m.content || "").slice(0, 2000)
          }))),
          { role: "user", content: "Question: " + question + "\n\nDataset context (JSON): " + JSON.stringify(summary) }
        ]
      })
    });
    if (!response.ok) {
      const errorBody = await response.text();
      return NextResponse.json({ error: response.status === 401 ? "The OpenAI API key was rejected. Check OPENAI_API_KEY." : "AI request failed (" + response.status + "). " + errorBody.slice(0, 300) }, { status: 502 });
    }
    const result = await response.json();
    const raw = result.choices?.[0]?.message?.content;
    if (!raw) return NextResponse.json({ error: "PULSE did not receive an answer. Try asking in a different way." }, { status: 502 });
    const parsed = JSON.parse(raw);
    let chart = null;
    if (parsed.chart && allowedGroups.has(parsed.chart.groupBy) && allowedMetrics.has(parsed.chart.metric) && allowedChartTypes.has(parsed.chart.chartType)) {
      chart = {
        title: String(parsed.chart.title || "Your requested analysis").slice(0, 100),
        description: String(parsed.chart.description || "").slice(0, 240),
        chartType: parsed.chart.chartType,
        groupBy: parsed.chart.groupBy,
        metric: parsed.chart.metric
      };
    }
    return NextResponse.json({
      answer: String(parsed.answer || "I couldn't form a reliable answer from these fields."),
      insight: String(parsed.insight || ""),
      chart
    });
  } catch (error: any) {
    return NextResponse.json({ error: error?.message || "Unable to process this question." }, { status: 500 });
  }
}
