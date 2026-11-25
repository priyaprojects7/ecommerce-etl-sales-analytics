"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Papa from "papaparse";
import * as XLSX from "xlsx";
import {
  Activity, ArrowDownRight, ArrowUpRight, Bell, Boxes, BriefcaseBusiness, CalendarDays,
  ChevronDown, ChevronRight, CircleHelp, Command, Download, FileSpreadsheet, Filter,
  LayoutDashboard, LifeBuoy, Menu, Package, PanelLeftClose, Plus, Search, Settings2,
  ShoppingBag, Sparkles, Target, TrendingUp, Upload, Users, Wallet, X, Zap, Bot, Send, MessageSquareText, History, Trash2, Bookmark, ChevronUp, PanelRightClose
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, Pie,
  LineChart, PieChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis
} from "recharts";

type RowData = Record<string, any>;
type Order = { id: string; date: Date; customer: string; city: string; category: string; product: string; qty: number; sales: number; cost: number; status: string };

const money = (n: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n || 0);
const shortMoney = (n: number) => n >= 1e6 ? "$" + (n/1e6).toFixed(2) + "m" : n >= 1000 ? "$" + (n/1000).toFixed(1) + "k" : money(n);
const palette = ["#9B8AFB", "#64C7B5", "#F6B96B", "#78A9FF", "#F28C9D", "#A8B8CB"];

function demoRows(): Order[] {
  const categories = ["Technology", "Home & Living", "Apparel", "Beauty", "Sports", "Grocery"];
  const products = ["Wireless headphones", "Smart watch", "Coffee maker", "Everyday hoodie", "Hydrating serum", "Yoga mat", "Desk lamp", "Running shoes", "Power bank", "Storage set", "Skin care kit", "Protein snacks"];
  const cities = ["New York", "Jersey City", "Boston", "Chicago", "Austin", "Seattle", "Atlanta"];
  const rows: Order[] = [];
  for (let i=0;i<420;i++) {
    const d = new Date(2025, Math.floor(i/36), 1 + ((i*7)%26));
    const category = categories[(i*7 + Math.floor(i/8))%categories.length];
    const product = products[(i*5)%products.length];
    const qty = 1 + ((i*3)%4);
    const sales = Math.round((24 + ((i*37)%280) + qty*19)*100)/100;
    rows.push({id:"ORD-"+(71000+i),date:d,customer:"Customer "+String(1+(i*13)%178).padStart(3,"0"),city:cities[(i*11)%cities.length],category,product,qty,sales,cost:sales*(.43+((i%7)*.025)),status:i%19===0?"Returned":i%11===0?"Pending":"Completed"});
  }
  return rows;
}

function buildGeneratedChartData(chart: any, rows: Order[]) {
  if (chart.chartType === "scatter") {
    const grouped = new Map<string, { units: number; sales: number }>();
    rows.forEach(r => { const v=grouped.get(r.product)||{units:0,sales:0}; v.units+=r.qty; v.sales+=r.sales; grouped.set(r.product,v); });
    return [...grouped.entries()].map(([name,v])=>({name,x:v.units?v.sales/v.units:0,y:v.units})).filter(v=>v.x>0&&v.y>0).slice(0,100);
  }
  const key = chart.groupBy || "category";
  const grouped = new Map<string,{sales:number;units:number;orders:Set<string>;sortKey:number}>();
  rows.forEach(r=>{
    const sortKey=key==="month"?new Date(r.date.getFullYear(),r.date.getMonth(),1).getTime():0;
    const name=key==="month"?r.date.toLocaleString("en-US",{month:"short",year:"numeric"}):String((r as any)[key]||"Unspecified");
    const v=grouped.get(name)||{sales:0,units:0,orders:new Set<string>(),sortKey};
    v.sales+=r.sales;v.units+=r.qty;v.orders.add(r.id);grouped.set(name,v);
  });
  const result=[...grouped.entries()].map(([name,v])=>({name,value:chart.metric==="orders"?v.orders.size:chart.metric==="units"?v.units:chart.metric==="average_order_value"?(v.orders.size?v.sales/v.orders.size:0):v.sales,sortKey:v.sortKey}));
  return (key==="month"?result.sort((a,b)=>a.sortKey-b.sortKey):result.sort((a,b)=>b.value-a.value)).slice(0,key==="month"?48:12);
}

const demo = demoRows();
const nav = [
  { label: "Overview", icon: LayoutDashboard, section: "WORKSPACE" },
  { label: "Sales intelligence", icon: TrendingUp },
  { label: "Customers", icon: Users },
  { label: "Products & inventory", icon: Package },
  { label: "Market & geography", icon: Target },
  { label: "Explore data", icon: Activity },
  { label: "What-if studio", icon: Zap, section: "ANALYSIS" },
  { label: "Reports", icon: FileSpreadsheet },
];

function normalizeRow(raw: RowData, i: number): Order | null {
  const find = (...keys: string[]) => {
    const wanted = keys.map(k=>k.toLowerCase().replace(/[^a-z0-9]/g,""));
    const key = Object.keys(raw).find(k=>wanted.includes(k.toLowerCase().replace(/[^a-z0-9]/g,"")));
    return key ? raw[key] : undefined;
  };
  const num = (v: any) => Number(String(v ?? "").replace(/[$,]/g,"")) || 0;
  const dateRaw = find("order_date","date","sample_order_date","invoice date","transaction date");
  const date = dateRaw ? new Date(dateRaw) : null;
  const sales = num(find("total_amount","sales","total","total sales","line_total","revenue","amount"));
  const qty = num(find("quantity","qty","units sold")) || 1;
  if (!sales && !find("total_amount","sales","total","total sales","line_total","revenue","amount")) return null;
  return {
    id:String(find("order_id","invoice id","invoice_id","transaction id","id") ?? "UPLOAD-"+(i+1)),
    date:date && !isNaN(date.getTime()) ? date : new Date(),
    customer:String(find("customer_name","customer","customer id","customer_id","customer type") ?? "Unspecified"),
    city:String(find("city","customer_city","shipping_city","shipping_address_city","billing_city","delivery_city","town","location","branch") ?? "Unspecified"),
    category:String(find("category","product line","product category") ?? "Uncategorized"),
    product:String(find("product","product_name","title","description") ?? "Unspecified product"),
    qty, sales, cost:num(find("cost","cogs","product_cost"))*qty,
    status:String(find("status","order_status","orderstatus","fulfillment_status","delivery_status","transaction_status","shipping_status") ?? "Recorded")
  };
}

export default function Home() {
  const [rows,setRows] = useState<Order[]>(demo);
  const [dataset,setDataset] = useState("Demo commerce dataset");
  const [active,setActive] = useState("Overview");
  const [range,setRange] = useState("All time");
  const [category,setCategory] = useState("All categories");
  const [statusFilter,setStatusFilter] = useState("All statuses");
  const [filtersOpen,setFiltersOpen] = useState(false);
  const [search,setSearch] = useState("");
  const [notice,setNotice] = useState("");
  const [sidebarOpen,setSidebarOpen] = useState(true);
  const [chatOpen,setChatOpen] = useState(false);
  const [chatInput,setChatInput] = useState("");
  const [chatBusy,setChatBusy] = useState(false);
  const [chatHistory,setChatHistory] = useState<any[]>([]);
  const [chatHistoryLoaded,setChatHistoryLoaded] = useState(false);
  const [chatChart,setChatChart] = useState<any>(null);
  const [whatIf,setWhatIf] = useState(8);
  const [metric,setMetric] = useState("Sales");
  const fileRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  useEffect(()=>{ try { const saved=localStorage.getItem("pulse-chat-history-v1"); if(saved) setChatHistory(JSON.parse(saved)); } catch {} finally { setChatHistoryLoaded(true); } },[]);
  useEffect(()=>{ if(chatHistoryLoaded) { try { localStorage.setItem("pulse-chat-history-v1",JSON.stringify(chatHistory)); } catch {} } },[chatHistory,chatHistoryLoaded]);
  useEffect(()=>{ chatEndRef.current?.scrollIntoView({behavior:"smooth"}); },[chatHistory,chatBusy]);

  const minDate = useMemo(()=>rows.reduce((m,r)=>r.date<m?r.date:m, rows[0]?.date ?? new Date()),[rows]);
  const maxDate = useMemo(()=>rows.reduce((m,r)=>r.date>m?r.date:m, rows[0]?.date ?? new Date()),[rows]);
  const filtered = useMemo(()=>{
    const cutoff = new Date(maxDate);
    if(range==="30 days") cutoff.setDate(cutoff.getDate()-30);
    if(range==="90 days") cutoff.setDate(cutoff.getDate()-90);
    if(range==="6 months") cutoff.setMonth(cutoff.getMonth()-6);
    if(range==="12 months") cutoff.setMonth(cutoff.getMonth()-12);
    return rows.filter(r=>(range==="All time" || r.date>=cutoff) && (category==="All categories" || r.category===category) &&
      (statusFilter==="All statuses" || r.status===statusFilter) &&
      (!search || [r.id,r.customer,r.product,r.city].join(" ").toLowerCase().includes(search.toLowerCase())));
  },[rows,range,category,statusFilter,search,maxDate]);
  const totalSales = filtered.reduce((a,r)=>a+r.sales,0);
  const totalOrders = new Set(filtered.map(r=>r.id)).size;
  const units = filtered.reduce((a,r)=>a+r.qty,0);
  const aov = totalOrders ? totalSales/totalOrders : 0;
  const hasCost = filtered.some(r=>r.cost>0);
  const profit = filtered.reduce((a,r)=>a+(r.sales-r.cost),0);
  const categories = [...new Set(rows.map(r=>r.category))].sort();
  const monthly = useMemo(()=>{
    const grouped = new Map<string,{month:string,sales:number,orders:Set<string>}>();
    filtered.forEach(r=>{const month=r.date.toLocaleString("en-US",{month:"short",year:"2-digit"});if(!grouped.has(month))grouped.set(month,{month,sales:0,orders:new Set()});const v=grouped.get(month)!;v.sales+=r.sales;v.orders.add(r.id);});
    return [...grouped.values()].map(v=>({month:v.month,sales:Math.round(v.sales),orders:v.orders.size})).sort((a,b)=>new Date("1 "+a.month).getTime()-new Date("1 "+b.month).getTime());
  },[filtered]);
  const categoryData = useMemo(()=>{
    const m=new Map<string,number>();filtered.forEach(r=>m.set(r.category,(m.get(r.category)||0)+r.sales));
    return [...m.entries()].map(([name,value])=>({name,value:Math.round(value)})).sort((a,b)=>b.value-a.value);
  },[filtered]);
  const topProducts = useMemo(()=>{
    const m=new Map<string,{name:string,sales:number,units:number}>();filtered.forEach(r=>{const v=m.get(r.product)||{name:r.product,sales:0,units:0};v.sales+=r.sales;v.units+=r.qty;m.set(r.product,v);});
    return [...m.values()].sort((a,b)=>b.sales-a.sales).slice(0,6);
  },[filtered]);
  const recent = [...filtered].sort((a,b)=>b.date.getTime()-a.date.getTime()).slice(0,7);
  const insights = [
    categoryData[0] ? categoryData[0].name+" leads the current selection with "+Math.round(categoryData[0].value/Math.max(totalSales,1)*100)+"% of sales." : "Upload data to generate insights.",
    topProducts[0] ? topProducts[0].name+" is your highest-selling product in this view." : "No product activity in this selection.",
    hasCost ? "Estimated gross margin is "+(profit/Math.max(totalSales,1)*100).toFixed(1)+"% based on the supplied cost fields." : "Add product cost or COGS fields to unlock margin analysis."
  ];

  async function handleUpload(file?: File) {
    if(!file) return;
    try {
      let raw: RowData[]=[];
      if(file.name.toLowerCase().endsWith(".csv")) {
        raw=await new Promise((resolve,reject)=>Papa.parse(file,{header:true,skipEmptyLines:true,complete:r=>resolve(r.data as RowData[]),error:reject}));
      } else if(file.name.match(/\.(xlsx|xls)$/i)) {
        const book=XLSX.read(await file.arrayBuffer(),{type:"array"});
        raw=XLSX.utils.sheet_to_json(book.Sheets[book.SheetNames[0]],{defval:""}) as RowData[];
      } else if(file.name.endsWith(".json")) {
        const json=JSON.parse(await file.text());raw=Array.isArray(json)?json:(json.data||json.orders||[]);
      } else throw new Error("Use CSV, Excel or JSON for now.");
      const normalized=raw.map(normalizeRow).filter(Boolean) as Order[];
      if(!normalized.length) throw new Error("I couldn't find a sales or total amount column. Try a file with columns such as Sales, Total, Revenue or total_amount.");
      setRows(normalized);setDataset(file.name);setRange("All time");setCategory("All categories");setSearch("");
      setNotice("Loaded "+normalized.length.toLocaleString()+" records. Some metrics depend on which columns your file contains.");
    } catch(e:any) {setNotice(e.message||"Could not read this file.");}
  }


  const chatAnalysis = useMemo(()=>{
    const summarize = (key:"category"|"product"|"customer"|"city"|"month") => {
      const groups = new Map<string,{sales:number;units:number;orders:Set<string>;customers:Set<string>}>();
      filtered.forEach(r=>{
        const name = key==="month" ? r.date.toLocaleString("en-US",{month:"short",year:"numeric"}) : String(r[key] || "Unspecified");
        const value = groups.get(name) || {sales:0,units:0,orders:new Set<string>(),customers:new Set<string>()};
        value.sales += r.sales; value.units += r.qty; value.orders.add(r.id); value.customers.add(r.customer);
        groups.set(name,value);
      });
      return [...groups.entries()].map(([name,v])=>({name,sales:Number(v.sales.toFixed(2)),units:v.units,orders:v.orders.size,customers:v.customers.size})).sort((a,b)=>b.sales-a.sales);
    };
    return {
      records:filtered.length,
      distinct_orders:new Set(filtered.map(r=>r.id)).size,
      distinct_customers:new Set(filtered.map(r=>r.customer)).size,
      distinct_products:new Set(filtered.map(r=>r.product)).size,
      total_sales:Number(filtered.reduce((a,r)=>a+r.sales,0).toFixed(2)),
      total_units:filtered.reduce((a,r)=>a+r.qty,0),
      total_cost:Number(filtered.reduce((a,r)=>a+r.cost,0).toFixed(2)),
      groups:{category:summarize("category"),product:summarize("product"),customer:summarize("customer"),city:summarize("city"),month:summarize("month")}
    };
  },[filtered]);

  async function askPulse(question?:string) {
    const q=(question??chatInput).trim(); if(!q||chatBusy) return;
    const userMsg={id:Date.now(),role:"user",content:q,createdAt:new Date().toISOString()};
    setChatHistory(prev=>[...prev,userMsg]);setChatInput("");setChatBusy(true);
    try {
      const response=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
        question:q,rows:filtered.slice(0,100).map(r=>({order_id:r.id,order_date:r.date.toISOString().slice(0,10),customer:r.customer,city:r.city,category:r.category,product:r.product,quantity:r.qty,sales:r.sales,cost:r.cost,status:r.status})),
        analysis:chatAnalysis,dataset,history:chatHistory.slice(-8).map(m=>({role:m.role,content:m.content}))
      })});
      const data=await response.json(); if(!response.ok) throw new Error(data.error||"The assistant could not answer this question.");
      const assistantMsg={id:Date.now()+1,role:"assistant",content:data.answer,createdAt:new Date().toISOString(),chart:data.chart||null,insight:data.insight||""};
      setChatHistory(prev=>[...prev,assistantMsg]);
    } catch(e:any) {
      setChatHistory(prev=>[...prev,{id:Date.now()+2,role:"assistant",content:e.message||"Something went wrong.",createdAt:new Date().toISOString()}]);
    } finally {setChatBusy(false);}
  }

  function exportRows() {
    const csv=["Order,Date,Customer,City,Category,Product,Units,Sales,Status",...filtered.map(r=>[r.id,r.date.toISOString().slice(0,10),r.customer,r.city,r.category,r.product,r.qty,r.sales,r.status].map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(","))].join("\n");
    const url=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));const a=document.createElement("a");a.href=url;a.download="pulse_filtered_analysis.csv";a.click();URL.revokeObjectURL(url);
  }

  return <main className="shell">
    <aside className={sidebarOpen?"sidebar":"sidebar collapsed"}>
      <div className="brand"><div className="brand-mark"><Activity size={19}/></div>{sidebarOpen&&<div><div className="brand-name">PULSE<span>.</span></div><div className="brand-sub">COMPANY INTELLIGENCE</div></div>}</div>
      <div className="workspace-switch"><div className="workspace-avatar">N</div>{sidebarOpen&&<><div className="workspace-copy"><b>Northstar Commerce</b><small>Workspace · Free plan</small></div><ChevronDown size={15}/></>}</div>
      {nav.map((item,i)=><div key={item.label}>{item.section&&sidebarOpen&&<div className="nav-section">{item.section}</div>}<button className={"nav-item "+(active===item.label?"active":"")} onClick={()=>setActive(item.label)} title={item.label}><item.icon size={17}/>{sidebarOpen&&<span>{item.label}</span>}{sidebarOpen&&active===item.label&&<span className="nav-dot"/>}</button></div>)}
      <div className="sidebar-bottom"><button className="nav-item"><Settings2 size={17}/>{sidebarOpen&&"Settings"}</button><button className="nav-item"><LifeBuoy size={17}/>{sidebarOpen&&"Help & support"}</button><div className="profile"><div className="profile-avatar">TS</div>{sidebarOpen&&<div><b>Thushara Siram</b><small>Personal workspace</small></div>}</div></div>
    </aside>
    <section className="main-area">
      <header className="topbar">
        <div className="top-left"><button className="icon-btn" onClick={()=>setSidebarOpen(!sidebarOpen)}><PanelLeftClose size={18}/></button><span className="crumb">Workspace</span><ChevronRight size={14}/><b>{active}</b></div>
        <div className="top-actions"><div className="searchbox"><Search size={15}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search orders, products, customers..."/><kbd>⌘ K</kbd></div><button className="chat-launch" onClick={()=>setChatOpen(true)}><Bot size={16}/> Ask PULSE</button><button className="icon-btn"><Bell size={17}/><i/></button><button className="avatar-small">TS</button></div>
      </header>
      <div className="content">
        <div className="page-heading">
          <div><div className="eyebrow"><span className="live-dot"/> BUSINESS PERFORMANCE <span className="eyebrow-divider">/</span> {dataset}</div><h1>{active==="Overview"?"Good afternoon. Here's your business.":active}</h1><p>See what's moving, understand why, and decide what to do next.</p></div>
          <div className="heading-actions"><button className="secondary-btn" onClick={()=>fileRef.current?.click()}><Upload size={15}/> Upload data</button><input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.json" hidden onChange={e=>handleUpload(e.target.files?.[0])}/><button className="primary-btn" onClick={exportRows}><Download size={15}/> Export view</button></div>
        </div>
        {notice&&<div className="notice"><span>{notice}</span><button onClick={()=>setNotice("")}><X size={14}/></button></div>}
        <div className="toolbar"><div className="dataset-label"><span className="file-icon"><FileSpreadsheet size={16}/></span><span><b>{dataset}</b><small>{rows.length.toLocaleString()} rows · {categories.length} categories</small></span><span className="connected">● Connected</span></div><div className="toolbar-right"><span className="muted-label"><CalendarDays size={14}/> Period</span><select value={range} onChange={e=>setRange(e.target.value)}><option>All time</option><option>12 months</option><option>6 months</option><option>90 days</option><option>30 days</option></select><select value={category} onChange={e=>setCategory(e.target.value)}><option>All categories</option>{categories.map(c=><option key={c}>{c}</option>)}</select><button className="filter-btn" onClick={()=>setFiltersOpen(v=>!v)} aria-expanded={filtersOpen}><Filter size={15}/> Filters <ChevronDown size={13}/></button></div></div>
        {filtersOpen&&<div className="filter-popover"><label>Order status<select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option>All statuses</option>{[...new Set(rows.map(r=>r.status))].sort().map(v=><option key={v}>{v}</option>)}</select></label><button className="secondary-btn compact" onClick={()=>{setStatusFilter("All statuses");setCategory("All categories");setSearch("");setRange("All time");}}>Clear filters</button><button className="text-btn" onClick={()=>setFiltersOpen(false)}>Done</button></div>}
        <div className="section-line"><span>PERFORMANCE SNAPSHOT</span><span className="updated">Updated just now <span>·</span> Live filters</span></div>
        <div className="kpi-grid">
          <Kpi title="Total sales" value={shortMoney(totalSales)} change="+12.8%" positive note="vs. previous period" icon={Wallet} tint="violet" spark={[24,32,28,42,37,55,49,68,63,78]}/>
          <Kpi title="Orders" value={totalOrders.toLocaleString()} change="+8.4%" positive note="vs. previous period" icon={ShoppingBag} tint="mint" spark={[34,28,38,36,50,44,58,55,70,78]}/>
          <Kpi title="Average order value" value={money(aov)} change="+3.2%" positive note="vs. previous period" icon={Target} tint="amber" spark={[60,54,62,58,70,67,72,76,73,84]}/>
          <Kpi title={hasCost?"Gross profit":"Units sold"} value={hasCost?shortMoney(profit):units.toLocaleString()} change={hasCost?"Margin data":"Across selected orders"} positive={hasCost} note={hasCost?"Estimated from supplied costs":"Quantity purchased"} icon={hasCost?TrendingUp:Boxes} tint="blue" spark={[22,31,29,44,40,52,48,63,67,75]}/>
        </div>
        <div className="grid-main">
          <div className="panel revenue-panel">
            <div className="panel-head"><div><div className="panel-kicker">REVENUE OVER TIME</div><h2>Sales performance</h2><p>Track how sales are trending across the selected period.</p></div><div className="panel-actions"><select value={metric} onChange={e=>setMetric(e.target.value)}><option>Sales</option><option>Orders</option></select><button className="dots">···</button></div></div>
            <div className="chart-legend"><span><i className="legend-violet"/> Sales</span><span><i className="legend-mint"/> Orders</span></div>
            <div className="revenue-chart"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={monthly} margin={{top:10,right:8,left:0,bottom:0}}><defs><linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#9B8AFB" stopOpacity={.28}/><stop offset="95%" stopColor="#9B8AFB" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#292B38" vertical={false}/><XAxis dataKey="month" tick={{fill:"#85899B",fontSize:11}} axisLine={false} tickLine={false}/><YAxis tickFormatter={v=>metric==="Sales"?shortMoney(v):v} tick={{fill:"#85899B",fontSize:11}} axisLine={false} tickLine={false} width={54}/><Tooltip contentStyle={{background:"#171923",border:"1px solid #343747",borderRadius:12,color:"#fff"}} formatter={(v:any)=>metric==="Sales"?money(v):v}/>{metric==="Sales"?<Area type="monotone" dataKey="sales" stroke="#9B8AFB" strokeWidth={2.5} fill="url(#salesFill)" activeDot={{r:5,fill:"#B5A9FF"}}/>:<Line type="monotone" dataKey="orders" stroke="#64C7B5" strokeWidth={2.5} dot={false} activeDot={{r:5}}/>}</ComposedChart></ResponsiveContainer></div>
            <div className="chart-foot"><span>Showing {filtered.length.toLocaleString()} records in current view</span><span className="chart-link" onClick={()=>setActive("Sales intelligence")}>View sales report <ChevronRight size={13}/></span></div>
          </div>
          <div className="panel insight-panel">
            <div className="panel-head"><div><div className="panel-kicker">PULSE SIGNALS</div><h2>What stands out</h2><p>Observations from your current data.</p></div><div className="signal-icon"><Sparkles size={17}/></div></div>
            <div className="insight-list">{insights.map((v,i)=><div className="insight" key={i}><div className={"insight-number n"+i}>{i===0?<TrendingUp size={15}/>:i===1?<Package size={15}/>:<CircleHelp size={15}/>}</div><div><b>{["Category leader","Product highlight","Data opportunity"][i]}</b><p>{v}</p></div></div>)}</div>
            <button className="text-btn" onClick={()=>setActive("Explore data")}>Explore insights <ChevronRight size={14}/></button>
          </div>
        </div>
        <div className="grid-bottom">
          <div className="panel category-panel"><div className="panel-head"><div><div className="panel-kicker">SALES MIX</div><h2>Where sales come from</h2><p>Category contribution to total sales.</p></div><button className="dots">···</button></div><div className="category-content"><div className="donut"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={categoryData} dataKey="value" nameKey="name" innerRadius={62} outerRadius={88} paddingAngle={3} stroke="none">{categoryData.map((v,i)=><Cell key={v.name} fill={palette[i%palette.length]}/>)}</Pie><Tooltip formatter={(v:any)=>money(v)}/></PieChart></ResponsiveContainer><div className="donut-center"><b>{shortMoney(totalSales)}</b><small>Total sales</small></div></div><div className="category-legend">{categoryData.slice(0,5).map((v,i)=><div className="legend-row" key={v.name}><span><i style={{background:palette[i%palette.length]}}/>{v.name}</span><b>{totalSales?Math.round(v.value/totalSales*100):0}%</b></div>)}</div></div></div>
          <div className="panel product-panel"><div className="panel-head"><div><div className="panel-kicker">PRODUCT PERFORMANCE</div><h2>Top-performing products</h2><p>Ranked by sales in the current selection.</p></div><button className="text-btn" onClick={()=>setActive("Products & inventory")}>View all <ChevronRight size={14}/></button></div><div className="product-list">{topProducts.slice(0,5).map((p,i)=><div className="product-row" key={p.name}><div className="product-rank">{String(i+1).padStart(2,"0")}</div><div className="product-info"><b>{p.name}</b><div className="bar-track"><div style={{width:(p.sales/Math.max(topProducts[0]?.sales||1,1)*100)+"%",background:palette[i%palette.length]}}/></div></div><div className="product-value"><b>{money(p.sales)}</b><small>{p.units} units</small></div></div>)}</div></div>
        </div>
        <div className="panel orders-panel"><div className="panel-head"><div><div className="panel-kicker">LATEST ACTIVITY</div><h2>Recent orders</h2><p>A quick look at the latest transactions in this view.</p></div><button className="secondary-btn compact" onClick={()=>setActive("Sales intelligence")}>All transactions <ChevronRight size={14}/></button></div><div className="table-wrap"><table><thead><tr><th>ORDER</th><th>DATE</th><th>CUSTOMER</th><th>LOCATION</th><th>PRODUCT</th><th>STATUS</th><th className="align-right">SALES</th></tr></thead><tbody>{recent.map((r,i)=><tr key={r.id+i}><td className="order-id">{r.id}</td><td>{r.date.toLocaleDateString("en-US",{month:"short",day:"2-digit",year:"numeric"})}</td><td>{r.customer}</td><td>{r.city}</td><td>{r.product}</td><td><span className={"status "+(r.status==="Completed"?"complete":r.status==="Returned"?"returned":"pending")}>{r.status}</span></td><td className="align-right amount">{money(r.sales)}</td></tr>)}</tbody></table></div></div>
        {chatHistory.filter((m:any)=>m.role==="assistant"&&m.chart).map((m:any)=><div className="panel ai-chart-panel" key={"chart-"+m.id}><div className="panel-head"><div><div className="panel-kicker">AI-GENERATED ANALYSIS</div><h2>{m.chart.title}</h2><p>{m.chart.description||"Built from the currently filtered dataset."}</p></div><span className="chart-type-label">{String(m.chart.chartType||"bar").toUpperCase()}</span></div><div className="ai-chart"><ResponsiveContainer width="100%" height="100%">{m.chart.chartType==="line"?<LineChart data={buildGeneratedChartData(m.chart,filtered)}><CartesianGrid stroke="#292d3b" vertical={false}/><XAxis dataKey="name" tick={{fill:"#a0a5b5",fontSize:10}}/><YAxis tick={{fill:"#858b9d",fontSize:10}}/><Tooltip/><Line type="monotone" dataKey="value" stroke="#9b8afb" strokeWidth={2.5}/></LineChart>:m.chart.chartType==="area"?<AreaChart data={buildGeneratedChartData(m.chart,filtered)}><CartesianGrid stroke="#292d3b" vertical={false}/><XAxis dataKey="name" tick={{fill:"#a0a5b5",fontSize:10}}/><YAxis tick={{fill:"#858b9d",fontSize:10}}/><Tooltip/><Area type="monotone" dataKey="value" stroke="#9b8afb" fill="#9b8afb" fillOpacity={0.2}/></AreaChart>:m.chart.chartType==="scatter"?<ScatterChart><CartesianGrid stroke="#292d3b"/><XAxis type="number" dataKey="x" name="Average unit price" tick={{fill:"#a0a5b5",fontSize:10}}/><YAxis type="number" dataKey="y" name="Units sold" tick={{fill:"#858b9d",fontSize:10}}/><Tooltip cursor={{strokeDasharray:"3 3"}}/><Scatter data={buildGeneratedChartData(m.chart,filtered)} fill="#9b8afb"/></ScatterChart>:m.chart.chartType==="pie"?<PieChart><Pie data={buildGeneratedChartData(m.chart,filtered)} dataKey="value" nameKey="name" outerRadius={105} label={(entry:any)=>{const values=buildGeneratedChartData(m.chart,filtered);const total=values.reduce((s:number,v:any)=>s+v.value,0);return entry.name+" "+(total?((entry.value/total)*100).toFixed(1):"0")+"%";}}>{buildGeneratedChartData(m.chart,filtered).map((v:any,i:number)=><Cell key={v.name} fill={palette[i%palette.length]}/>)}</Pie><Tooltip/></PieChart>:<BarChart layout={m.chart.orientation==="horizontal"?"vertical":"horizontal"} data={buildGeneratedChartData(m.chart,filtered)} margin={{top:10,right:18,left:12,bottom:10}}><CartesianGrid stroke="#292d3b" vertical={m.chart.orientation==="horizontal"} horizontal={m.chart.orientation!=="horizontal"}/>{m.chart.orientation==="horizontal"?<><XAxis type="number" tick={{fill:"#858b9d",fontSize:10}}/><YAxis type="category" dataKey="name" width={150} tick={{fill:"#a0a5b5",fontSize:10}}/></>:<><XAxis dataKey="name" tick={{fill:"#a0a5b5",fontSize:10}} axisLine={false} tickLine={false}/><YAxis tick={{fill:"#858b9d",fontSize:10}} axisLine={false} axisLine={false} tickLine={false}/></>}<Tooltip contentStyle={{background:"#171923",border:"1px solid #343747",borderRadius:12}}/><Bar dataKey="value" fill="#9b8afb" radius={m.chart.orientation==="horizontal"?[0,6,6,0]:[6,6,0,0]}/></BarChart>}</ResponsiveContainer></div><div className="chart-explanation"><b>Insight &amp; interpretation</b><p>{m.insight||m.chart.description||"Review the displayed pattern against the selected date range and filters."}</p><small>Chart data is recalculated from the current dashboard filters.</small></div></div>)}
        <footer><span>© 2026 PULSE Intelligence</span><span>Numbers are based on the selected dataset and filters. Verify source definitions before making business decisions.</span></footer>
      </div>
    </section>
  
    {chatOpen&&<div className="chat-overlay">
      <div className="chat-backdrop" onClick={()=>setChatOpen(false)}></div>
      <aside className="chat-drawer">
        <div className="chat-header"><div className="chat-brand"><div className="chat-brand-icon"><Bot size={18}/></div><div><b>Ask PULSE</b><small>AI data analyst · {dataset}</small></div></div><div className="chat-header-actions"><button title="Clear chat history" onClick={()=>{if(confirm("Clear all saved PULSE conversations from this browser?")){setChatHistory([]);}}}><Trash2 size={16}/></button><button onClick={()=>setChatOpen(false)}><X size={18}/></button></div></div>
        <div className="chat-context"><Sparkles size={14}/> Answers use your current filters and uploaded dataset.</div>
        <div className="chat-messages">
          {chatHistory.length===0&&<div className="chat-welcome"><div className="chat-welcome-icon"><Sparkles size={23}/></div><h3>What would you like to understand?</h3><p>Ask about performance, compare groups, find patterns, or request a chart. I'll explain the result and show the data behind it.</p><div className="prompt-chips">{["Which category drives the most sales?","Show monthly sales trend","Compare sales by city","Which products need attention?","Explain average order value"].map(q=><button key={q} onClick={()=>askPulse(q)}>{q}<ChevronRight size={13}/></button>)}</div></div>}
          {chatHistory.map((m:any)=><div className={"chat-message "+m.role} key={m.id}><div className="message-avatar">{m.role==="assistant"?<Bot size={15}/>:<span>TS</span>}</div><div className="message-body"><div className="message-role">{m.role==="assistant"?"PULSE":"YOU"} <span>{new Date(m.createdAt).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}</span></div><p>{m.content}</p>{m.chart&&<button className="inline-chart-btn" onClick={()=>{setChatOpen(false);document.querySelector(".ai-chart-panel")?.scrollIntoView({behavior:"smooth",block:"start"});}}> <TrendingUp size={14}/> Show chart on dashboard</button>}</div></div>)}
          {chatBusy&&<div className="chat-message assistant"><div className="message-avatar"><Bot size={15}/></div><div className="typing"><i/><i/><i/></div></div>}
          <div ref={chatEndRef}/>
        </div>
        <div className="chat-composer"><textarea value={chatInput} onChange={e=>setChatInput(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();askPulse();}}} placeholder="Ask anything about your business data..." rows={2}/><div className="composer-bottom"><span>Enter to send · Shift + Enter for a new line</span><button disabled={!chatInput.trim()||chatBusy} onClick={()=>askPulse()}><Send size={15}/></button></div></div>
        <div className="chat-footer"><History size={12}/> Conversations are saved in this browser for later reference.</div>
      </aside>
    </div>}

  </main>;
}

function Kpi({title,value,change,positive,note,icon:Icon,tint,spark}:{title:string,value:string,change:string,positive:boolean,note:string,icon:any,tint:string,spark:number[]}) {
  return <div className="kpi-card"><div className="kpi-top"><span>{title}</span><div className={"kpi-icon "+tint}><Icon size={17}/></div></div><div className="kpi-value">{value}</div><div className="kpi-bottom"><span className={positive?"positive":"neutral"}>{positive?<ArrowUpRight size={14}/>:<ArrowDownRight size={14}/>} {change}</span><small>{note}</small><div className="spark">{spark.map((v,i)=><i key={i} style={{height:v+"%"}}/>)}</div></div></div>;
}
