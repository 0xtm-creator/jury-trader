"use client";
import { useState } from "react";

interface RewindData {
  start_date: string; days_ago: number; investment: number;
  start_price: number; end_price: number; bnb_bought: number;
  hold_return_pct: number; hold_final_value: number;
  strategy: string; strategy_return_pct: number; strategy_trades: number;
  equity_curve: number[];
}

export default function Home() {
  const [data, setData] = useState<RewindData | null>(null);
  const [loading, setLoading] = useState(false);
  const [daysAgo, setDaysAgo] = useState(180);
  const [amount, setAmount] = useState(1000);
  const [strategy, setStrategy] = useState("ma_cross");

  const runRewind = async () => {
    setLoading(true);
    const res = await fetch(`/api/rewind?days_ago=${daysAgo}&investment=${amount}&strategy=${strategy}`);
    const d = await res.json();
    setData(d);
    setLoading(false);
  };

  const diff = data ? data.strategy_return_pct - data.hold_return_pct : 0;

  return (
    <main className="min-h-screen bg-[#0a0e17] text-white p-6">
      <div className="max-w-3xl mx-auto">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-black mb-2">🔮 RewindTrader</h1>
          <p className="text-slate-400 text-lg">What if you invested differently in the past?</p>
        </header>

        {/* Controls */}
        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-5 mb-6">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Days Ago</label>
              <div className="flex gap-1 flex-wrap">
                {[30, 90, 180, 365].map(d => (
                  <button key={d} onClick={() => setDaysAgo(d)}
                    className={`px-3 py-1.5 text-xs rounded font-mono ${daysAgo === d ? "bg-purple-500 text-white font-bold" : "bg-gray-700 text-slate-300"}`}>{d}d</button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Investment ($)</label>
              <div className="flex gap-1 flex-wrap">
                {[100, 500, 1000, 5000].map(a => (
                  <button key={a} onClick={() => setAmount(a)}
                    className={`px-3 py-1.5 text-xs rounded font-mono ${amount === a ? "bg-purple-500 text-white font-bold" : "bg-gray-700 text-slate-300"}`}>${a}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Strategy</label>
              <select value={strategy} onChange={e => setStrategy(e.target.value)}
                className="bg-gray-700 text-white text-xs rounded px-3 py-2 w-full">
                <option value="hold">Buy & Hold</option>
                <option value="ma_cross">MA Crossover</option>
                <option value="dca">DCA (Weekly)</option>
              </select>
            </div>
          </div>
          <button onClick={runRewind} disabled={loading}
            className="w-full py-3 bg-purple-500 hover:bg-purple-400 text-white font-bold rounded-lg disabled:opacity-50 text-lg">
            {loading ? "⏳ Simulating..." : "⏪ Rewind Time"}
          </button>
        </div>

        {/* Results */}
        {data && (
          <div className="space-y-4">
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-5 text-center">
              <p className="text-slate-400 text-sm">{data.start_date} → Today</p>
              <p className="text-3xl font-black mt-1">
                ${data.investment} → <span className={data.strategy_return_pct >= 0 ? "text-green-400" : "text-red-400"}>
                  ${data.hold_final_value.toFixed(2)}
                </span>
              </p>
              <p className={`text-lg font-bold ${data.strategy_return_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                {data.strategy_return_pct >= 0 ? "+" : ""}{data.strategy_return_pct.toFixed(2)}%
              </p>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-center">
                <div className="text-xs text-slate-400">BNB Price</div>
                <div className="text-sm text-slate-400">${data.start_price.toFixed(2)} → <span className="text-white font-bold">${data.end_price.toFixed(2)}</span></div>
              </div>
              <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-center">
                <div className="text-xs text-slate-400">BNB Bought</div>
                <div className="text-xl font-bold text-white font-mono">{data.bnb_bought.toFixed(4)}</div>
              </div>
              <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4 text-center">
                <div className="text-xs text-slate-400">vs Buy&Hold</div>
                <div className={`text-xl font-bold font-mono ${diff >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {diff >= 0 ? "+" : ""}{diff.toFixed(1)}%
                </div>
              </div>
            </div>

            {data.strategy !== "hold" && (
              <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4">
                <div className="text-sm text-slate-300 font-bold mb-2">
                  {data.strategy === "ma_cross" ? "MA Crossover" : "Weekly DCA"} · {data.strategy_trades} trades
                </div>
                {/* Simple equity curve as bars */}
                <div className="flex items-end gap-[1px] h-32">
                  {data.equity_curve.filter((_, i) => i % Math.ceil(data.equity_curve.length / 80) === 0).map((v, i) => {
                    const h = Math.max(2, ((v - data.investment) / data.investment) * 80 + 50);
                    return <div key={i} className="flex-1 rounded-t"
                      style={{ height: `${Math.max(1, h)}%`, background: v >= data.investment ? "#22c55e" : "#ef4444", opacity: 0.7 }} />;
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
