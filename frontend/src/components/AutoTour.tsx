"use client";

import { useEffect, useState, useRef } from "react";

export default function AutoTour({ onSkip }: { onSkip: () => void }) {
  const [subtitle, setSubtitle] = useState("");
  const [visible, setVisible] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);
  const onSkipRef = useRef(onSkip);
  onSkipRef.current = onSkip;

  useEffect(() => {
    const run = async () => {
      const wait = (ms: number) => new Promise(r => setTimeout(r, ms));
      const hide = () => { setVisible(false); return wait(350); };

      const steps: Array<{ text: string; action: () => void; dur: number }> = [
        {
          text: "Welcome to RewindTrader · Turn back time and replay your BNB investments — what if you had traded differently?",
          action: () => scrollToTop(),
          dur: 4000,
        },
        {
          text: "Set your time machine: rewind 90 days into the past. See how BNB performed and how you could have profited",
          action: () => clickPill("90d"),
          dur: 4500,
        },
        {
          text: "Choose your investment — from one hundred to five thousand dollars. Let's start with $1,000",
          action: () => clickPill("$1000"),
          dur: 3500,
        },
        {
          text: "Six strategies available: Buy & Hold, MA Crossover, DCA Weekly, RSI Signal, Bollinger Bands, and MACD Cross",
          action: () => scrollTo(".grid-cols-3"),
          dur: 4000,
        },
        {
          text: "Try Dollar-Cost Averaging — invest equal amounts every week, rain or shine. Smooths out volatility automatically",
          action: () => clickStrategy("DCA Weekly"),
          dur: 5000,
        },
        {
          text: "DCA results are in! Compare strategy return vs simple Buy & Hold. See exactly how many BNB you would have accumulated",
          action: () => scrollTo(".space-y-4"),
          dur: 5000,
        },
        {
          text: "Now switch to RSI Signal strategy — buying when the market is oversold, selling when overbought. Timing the cycles",
          action: () => clickStrategy("RSI Signal"),
          dur: 5500,
        },
        {
          text: "The RSI strategy trades less frequently but aims for higher quality entries. Compare the equity curve to DCA",
          action: () => scrollTo(".h-32"),
          dur: 5000,
        },
        {
          text: "Try Bollinger Bands — buying at the lower band and selling at the upper band. Capturing mean reversion profitably",
          action: () => clickStrategy("Bollinger"),
          dur: 5500,
        },
        {
          text: "Now look back a full year — 365 days. See how strategies perform across entire market cycles, bull and bear",
          action: () => clickPill("365d"),
          dur: 5500,
        },
        {
          text: "The equity curve visualizes every dollar of your journey — green means profit above your investment, red means loss",
          action: () => scrollTo(".h-32"),
          dur: 4500,
        },
        {
          text: "RewindTrader · What if you invested differently? Now you know. Built for BNB Hack 2026",
          action: () => scrollToTop(),
          dur: 5000,
        },
      ];

      for (let i = 0; i < steps.length; i++) {
        setStepIdx(i);
        await hide();
        const step = steps[i];
        setSubtitle(step.text);
        step.action();
        await wait(200);
        setVisible(true);
        await wait(step.dur);
      }
      await hide();
      onSkipRef.current();
    };

    const t = setTimeout(run, 2000);
    return () => clearTimeout(t);
  }, []);

  return (
    <>
      <div className={`fixed bottom-10 left-1/2 -translate-x-1/2 z-[200] transition-all duration-400 pointer-events-none ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
      }`}>
        <div className="text-white text-2xl font-bold text-center max-w-4xl leading-relaxed"
          style={{ textShadow: "0 2px 12px rgba(0,0,0,0.9), 0 0 40px rgba(0,0,0,0.7)" }}>
          {subtitle}
        </div>
      </div>
      <div className="fixed top-4 right-4 z-[200] flex items-center gap-3">
        <span className="text-xs text-slate-400 bg-black/60 px-2 py-1 rounded-full">{stepIdx + 1}/12</span>
        <button onClick={onSkipRef.current} className="bg-white/10 hover:bg-white/20 text-white text-xs px-3 py-1.5 rounded-full transition-colors backdrop-blur">Skip Tour →</button>
      </div>
    </>
  );
}

function scrollToTop() { window.scrollTo({ top: 0, behavior: "smooth" }); }
function scrollTo(sel: string) {
  try { document.querySelector(sel)?.scrollIntoView({ behavior: "smooth", block: "center" }); } catch {}
}
function clickPill(label: string) {
  try {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent?.trim() === label) (b as HTMLElement).click();
    });
  } catch {}
}
function clickStrategy(name: string) {
  try {
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent?.includes(name)) (b as HTMLElement).click();
    });
  } catch {}
}
