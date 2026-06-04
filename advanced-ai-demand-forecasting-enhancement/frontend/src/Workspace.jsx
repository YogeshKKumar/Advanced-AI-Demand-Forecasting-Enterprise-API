import React, { useCallback, useEffect, useState } from "react";
import gateway from "./services/gateway";
import { useIdentity } from "./state/IdentityProvider";
import EntryScreen from "./views/EntryScreen";
import ControlShell from "./views/ControlShell";
import OverviewDesk from "./views/OverviewDesk";
import ImportDesk from "./views/ImportDesk";
import ScenarioDesk from "./views/ScenarioDesk";
import ExportDesk from "./views/ExportDesk";
import AdminDesk from "./views/AdminDesk";

export default function Workspace() {
  const { account } = useIdentity();
  const [desk, setDesk] = useState("overview");
  const [workbooks, setWorkbooks] = useState([]);
  const [activeWorkbook, setActiveWorkbook] = useState("");
  const [insights, setInsights] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [busy, setBusy] = useState(false);

  const loadWorkbooks = useCallback(async () => {
    const { data } = await gateway.get("/workbooks?size=100");
    setWorkbooks(data.records || []);
    if (!activeWorkbook && data.records?.length) setActiveWorkbook(String(data.records[0].id));
  }, [activeWorkbook]);

  const loadAlerts = useCallback(async () => {
    const { data } = await gateway.get("/alerts");
    setAlerts(data);
  }, []);

  const loadInsights = useCallback(async () => {
    if (!activeWorkbook) {
      setInsights(null);
      return;
    }
    setBusy(true);
    try {
      const { data } = await gateway.get(`/insights/${activeWorkbook}`);
      setInsights(data);
    } finally {
      setBusy(false);
    }
  }, [activeWorkbook]);

  const refresh = async () => {
    await loadWorkbooks();
    await loadAlerts();
    await loadInsights();
  };

  useEffect(() => {
    if (account) {
      loadWorkbooks();
      loadAlerts();
    }
  }, [account, loadWorkbooks, loadAlerts]);

  useEffect(() => {
    if (account) loadInsights();
  }, [account, loadInsights]);

  if (!account) return <EntryScreen />;

  const shared = { workbooks, activeWorkbook, setActiveWorkbook, insights, busy, refresh };

  return (
    <ControlShell desk={desk} setDesk={setDesk} alerts={alerts} refreshAlerts={loadAlerts}>
      {desk === "overview" && <OverviewDesk {...shared} />}
      {desk === "import" && <ImportDesk afterImport={async (id) => { setActiveWorkbook(String(id)); await refresh(); setDesk("scenarios"); }} />}
      {desk === "scenarios" && <ScenarioDesk {...shared} />}
      {desk === "exports" && <ExportDesk {...shared} />}
      {desk === "admin" && <AdminDesk />}
    </ControlShell>
  );
}
