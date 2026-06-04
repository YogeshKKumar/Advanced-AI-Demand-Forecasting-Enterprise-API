import React from "react";
import { X } from "lucide-react";

export default function Modal({ title, open, onClose, children }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop">
      <section className="modal-panel">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="text-lg font-black">{title}</h3>
          <button className="icon-button" onClick={onClose} title="Close"><X size={18}/></button>
        </div>
        {children}
      </section>
    </div>
  );
}


