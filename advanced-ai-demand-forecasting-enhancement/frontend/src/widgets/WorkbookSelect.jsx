import React from "react";

export default function WorkbookSelect({ workbooks, value, onChange }) {
  return (
    <select className="field min-w-72" value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">Choose workbook</option>
      {workbooks.map((workbook) => <option value={workbook.id} key={workbook.id}>{workbook.title}</option>)}
    </select>
  );
}
