import { NextRequest, NextResponse } from "next/server";

const allowedGroups = new Set(["category", "product", "customer", "city", "month"]);
const allowedMetrics = new Set(["sales", "orders", "units", "average_order_value"]);

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const question = String(body.question || "").trim();
    const rows = Array.isArray(body.rows) ? body.rows.slice(0, 250) : [];
    if (!question) return NextResponse.json({ error: "Enter a question first." }, { status: 400 });
    if (!rows.length) return NextResponse.json({ error: "There are no rows in the current filters. Adjust the filters or upload data first." }, { status: 400 });

    const totals = rows.reduce((a: any, r: any) => {
      a.sales += Number(r.sales) || 0;
      a.units += Number(r.quantity) || 0;
      a.orders.add(String(r.order_id));
      a.categories.add(String(r.category || "Unspecified"));
      a.cities.add(String(r.city || "Unspecified"));
      a.products.add(String(r.product || "Unspecified"));
      return a;
    }, { sales: 0, units: 0, orders: new Set<string>(), categories: new Set<string>(), cities: new Set<string>(), products: new Set<string>() });

    const summary = {
      dataset: String(body.dataset || "Uploaded dataset"),
      records_in_context: rows.length,
      distinct_orders: totals.orders.size,
      sales_sum: Number(totals.sales.toFixed(2)),
      units_sum: totals.units,
      categories: [...totals.categories].slice(0, 50),
      cities: [...totals.cities].slice(0, 50),
      products: [...totals.products].slice(0, 50),
      rows
    };

    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      return NextResponse.json({
        error: "PULSE AI needs an OpenAI API key. Add OPENAI_API_KEY to web/.env.local, restart the app, and try again. Your question history will still be saved in this browser."
      }, { status: 503 });
    }

    const system = `You are PULSE, a careful business data analyst. Answer only from the supplied dataset context. Never invent missing fields, values, causes, or business facts. The data context may be a filtered sample (maximum 250 rows); say so when relevant. If a requested metric cannot be computed from available fields, explain which field is missing. Distinguish sales from profit. Only estimate gross profit if cost values are actually present and meaningful. Return valid JSON only with this exact shape:
{"answer":"plain language response with specific numbers and caveats","insight":"one short practical observation or limitation","chart":null}
If a chart would materially help, chart must be {"title":"short chart title","description":"what the chart shows and any limitation","groupBy":"category|product|customer|city|month","metric":"sales|orders|units|average_order_value"}. Choose only these allowed values. Use chart=null if the question is explanatory or a chart would not help. For questions asking for top/bottom items, choose the appropriate group and metric; chart renders top 10. Do not include markdown fences.`;

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
    if (parsed.chart && allowedGroups.has(parsed.chart.groupBy) && allowedMetrics.has(parsed.chart.metric)) {
      chart = {
        title: String(parsed.chart.title || "Your requested analysis").slice(0, 100),
        description: String(parsed.chart.description || "").slice(0, 240),
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
