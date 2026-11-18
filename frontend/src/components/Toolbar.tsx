interface Props {
  onCalculate: () => void;
  onOptimize: () => void;
  onOptimizeStops: () => void;
  onNextDay: () => void;
  onExport: () => void;
  onGeocode: () => void;
  geocoding: boolean;
  calculating: boolean;
  optimizing: boolean;
  optimizingStops: boolean;
  exporting: boolean;
  hasOrders: boolean;
  optimizeAll: boolean;
  onOptimizeAllChange: (value: boolean) => void;
}

export default function Toolbar({
  onCalculate,
  onOptimize,
  onOptimizeStops,
  onNextDay,
  onExport,
  onGeocode,
  geocoding,
  calculating,
  optimizing,
  optimizingStops,
  exporting,
  hasOrders,
  optimizeAll,
  onOptimizeAllChange,
}: Props) {
  const busy = calculating || optimizing || optimizingStops || exporting || geocoding;

  return (
    <div className="toolbar-block">
      <div className="toolbar">
        <button
          onClick={onGeocode}
          disabled={!hasOrders || busy}
          title="Find map coordinates for order addresses (fills missing ones from the address register)"
        >
          {geocoding ? "Locating…" : "Locate addresses"}
        </button>
        <button
          className="btn-primary"
          onClick={onOptimize}
          disabled={!hasOrders || busy}
        >
          {optimizing ? "Optimizing…" : "Optimize routes"}
        </button>
        <button onClick={onOptimizeStops} disabled={!hasOrders || busy}>
          {optimizingStops ? "Sequencing…" : "Optimize stop order"}
        </button>
        <button onClick={onCalculate} disabled={!hasOrders || busy}>
          {calculating ? "Calculating…" : "Calculate plan"}
        </button>
        <button onClick={onNextDay} disabled={!hasOrders || busy}>
          Create next day plan
        </button>
        <button onClick={onExport} disabled={!hasOrders || busy}>
          {exporting ? "Exporting…" : "Export driver sheets"}
        </button>
      </div>
      <label className="toolbar-option">
        <input
          type="checkbox"
          checked={optimizeAll}
          onChange={(e) => onOptimizeAllChange(e.target.checked)}
          disabled={!hasOrders || busy}
        />
        Include already assigned orders when optimizing routes
      </label>
    </div>
  );
}
