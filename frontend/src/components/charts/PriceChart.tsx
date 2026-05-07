import { useEffect, useRef } from "react";
import { createChart, CandlestickSeries, HistogramSeries, type IChartApi, type ISeriesApi } from "lightweight-charts";
import type { Candle } from "@/api/client";

export function PriceChart({ candles, height = 380 }: { candles: Candle[]; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: {
        background: { color: "transparent" },
        textColor: "#a1a1aa",
        fontFamily: "Inter, sans-serif",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;

    candleRef.current = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#f43f5e",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#f43f5e",
    });

    volRef.current = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

    return () => { chart.remove(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    if (!candleRef.current || !volRef.current) return;
    const cs = candles.map((c) => ({
      time: Math.floor(new Date(c.time).getTime() / 1000) as any,
      open: c.open, high: c.high, low: c.low, close: c.close,
    }));
    const vs = candles.map((c) => ({
      time: Math.floor(new Date(c.time).getTime() / 1000) as any,
      value: c.volume,
      color: c.close >= c.open ? "rgba(16,185,129,0.4)" : "rgba(244,63,94,0.4)",
    }));
    candleRef.current.setData(cs);
    volRef.current.setData(vs);
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  return <div ref={ref} style={{ height, width: "100%" }} />;
}
