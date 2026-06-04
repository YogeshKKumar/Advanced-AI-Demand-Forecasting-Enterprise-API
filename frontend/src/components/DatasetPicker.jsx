import React from "react";

export default function DatasetPicker({ datasets, selectedDatasetId, setSelectedDatasetId }) {
  return (
    <select value={selectedDatasetId} onChange={(event) => setSelectedDatasetId(event.target.value)} className="input min-w-64">
      <option value="">Select dataset</option>
      {datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}
    </select>
  );
}


