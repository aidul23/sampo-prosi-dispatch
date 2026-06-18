interface Props {
  onCalculate: () => void;
  onNextDay: () => void;
  onExport: () => void;
  calculating: boolean;
  exporting: boolean;
  hasOrders: boolean;
}

export default function Toolbar({
  onCalculate,
  onNextDay,
  onExport,
  calculating,
  exporting,
  hasOrders,
}: Props) {
  return (
    <div className="toolbar">
      <button className="btn-primary" onClick={onCalculate} disabled={!hasOrders || calculating}>
        {calculating ? "Calculating…" : "Calculate plan"}
      </button>
      <button onClick={onNextDay} disabled={!hasOrders}>
        Create next day plan
      </button>
      <button onClick={onExport} disabled={!hasOrders || exporting}>
        {exporting ? "Exporting…" : "Export driver sheets"}
      </button>
    </div>
  );
}
