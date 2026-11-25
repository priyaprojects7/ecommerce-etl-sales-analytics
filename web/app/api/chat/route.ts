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
    const q = question.toLowerCase();
    const requestedChartType = /\bscatter\b/.test(q) ? "scatter" : /\barea\b/.test(q) ? "area" : /\bline\b/.test(q) ? "line" : /\bpie\b|\bdonut\b/.test(q) ? "pie" : /\bbar\b/.test(q) ? "bar" : null;
    const chartRequested = Boolean(requestedChartType || /\b(chart|graph|plot|visuali[sz]e)\b/.test(q));
    const inferredGroup = /\b(month|monthly|over time|trend|time series|last \d+ months?|past \d+ months?)\b/.test(q) ? "month" : /\b(city|cities|location|geograph)\b/.test(q) ? "city" : /\bcustomer\b/.test(q) ? "customer" : /\bproduct\b/.test(q) ? "product" : "category";
    const inferredMetric = /\b(order volume|number of orders|orders)\b/.test(q) ? "orders" : /\b(units|quantity|volume sold)\b/.test(q) ? "units" : /\baverage order value|aov\b/.test(q) ? "average_order_value" : "sales";
    const chartSource = parsed.chart && allowedGroups.has(parsed.chart.groupBy) && allowedMetrics.has(parsed.chart.metric) && allowedChartTypes.has(parsed.chart.chartType) ? parsed.chart : null;
    const requestedType = requestedChartType || (chartSource ? chartSource.chartType : "bar");
    const wantsOnePerProduct = /\b(each|one per|one for each)\b/.test(q) && /\b(products?|product)\b/.test(q) && /\b(top|highest|best)\b/.test(q);
    const monthWindowMatch = q.match(/(?:last|past)\s+(\d+)\s+months?/);
    const dateWindowMonths = monthWindowMatch ? Math.max(1,Math.min(24,Number(monthWindowMatch[1]))) : null;
    let charts: any[] = [];
    let chart = null;
    if (chartRequested) {
      const scatterRequested = requestedType === "scatter";
      const groupBy = scatterRequested ? "product" : (chartSource?.groupBy || inferredGroup);
      const metric = scatterRequested ? "units" : (chartSource?.metric || inferredMetric);
      const metricLabel = metric === "orders" ? "Order volume" : metric === "units" ? "Units sold" : metric === "average_order_value" ? "Average order value" : "Revenue";
      chart = {
        title: String(chartSource?.title || (scatterRequested ? "Average selling price vs. units sold" : groupBy === "month" ? (metric === "orders" ? "Monthly order volume" : "Monthly sales trend") : metricLabel + " by " + groupBy).trim()).slice(0, 100),
        description: String(chartSource?.description || (scatterRequested ? "Each point represents a product. Average selling price is calculated as product revenue divided by units sold." : groupBy === "month" ? "Monthly values are calculated from the date and order fields and displayed in chronological order." : "Calculated from the current filtered dataset.")).slice(0, 240),
        chartType: requestedType, groupBy, metric, orientation: /\bhorizontal\b/.test(q) ? "horizontal" : "vertical"
      };
    }
    if (chartRequested && wantsOnePerProduct) {
      const products = Array.isArray(analysis.groups?.product) ? analysis.groups.product.slice().sort((a:any,b:any)=>Number(b.sales)-Number(a.sales)).slice(0,5) : [];
      charts = products.map((product:any)=>({
        title: String(product.name + " · Monthly performance").slice(0,100),
        description: dateWindowMonths ? "Monthly revenue for this product over the last " + dateWindowMonths + " months in the available dataset." : "Monthly revenue for this product, calculated from the uploaded records.",
        chartType: requestedType === "bar" ? "bar" : requestedType,
        groupBy: "month",
        metric: "sales",
        productName: String(product.name),
        dateWindowMonths,
        orientation: /\bhorizontal\b/.test(q) ? "horizontal" : "vertical"
      }));
    }
    const modelAnswer = String(parsed.answer || "I couldn't form a reliable answer from these fields.");
    const hasGeneratedChart = Boolean(chart || charts.length);
    const answer = hasGeneratedChart && /cannot|can't|unable|not available|not provided|not possible|does not provide|does not contain|lack(s|ing)? the necessary|without a breakdown/i.test(modelAnswer)
      ? charts.length ? "I've generated five separate monthly performance charts, one for each of the top five products, using the available date, sales and product fields." : "I've generated the requested chart using the available fields in your uploaded dataset. The chart values are calculated from the current filters."
      : modelAnswer;
    return NextResponse.json({
      answer,
      insight: String(parsed.insight || ""),
      chart: charts.length ? null : chart,
      charts
    });
  } catch (error: any) {
    return NextResponse.json({ error: error?.message || "Unable to process this question." }, { status: 500 });
  }
}
