import React, { useCallback, useEffect, useMemo, useState } from "react";
import api from "./api/client";
import Layout from "./components/Layout";
import { useAuth } from "./state/AuthContext";
import AdminPage from "./views/AdminPage";
import AuthPage from "./views/AuthPage";
import DashboardPage from "./views/DashboardPage";
import ForecastPage from "./views/ForecastPage";
import ReportsPage from "./views/ReportsPage";
import UploadPage from "./views/UploadPage";

export default function App() {
  const { user } = useAuth();
  const [activePage, setActivePage] = useState("dashboard");
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [datasetFilters, setDatasetFilters] = useState({ products: [], categories: [], regions: [] });
  const [filters, setFilters] = useState({ start_date: "", end_date: "", category: "", region: "" });
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadDatasets = useCallback(async () => {
    const { data } = await api.get("/datasets?page_size=100&sort_by=created_at&sort_dir=desc");
    setDatasets(data.items || []);
    if (!selectedDatasetId && data.items?.length) setSelectedDatasetId(String(data.items[0].id));
  }, [selectedDatasetId]);

  const loadNotifications = useCallback(async () => {
    const { data } = await api.get("/notifications");
    setNotifications(data);
  }, []);

  const loadAnalytics = useCallback(async () => {
    if (!selectedDatasetId) {
      setAnalytics(null);
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
      const { data } = await api.get(`/analytics/${selectedDatasetId}?${params.toString()}`);
      setAnalytics(data);
    } finally {
      setLoading(false);
    }
  }, [selectedDatasetId, filters]);

  const loadFilters = useCallback(async () => {
    if (!selectedDatasetId) return;
    const { data } = await api.get(`/datasets/${selectedDatasetId}/filters`);
    setDatasetFilters(data);
  }, [selectedDatasetId]);

  useEffect(() => {
    if (user) {
      loadDatasets();
      loadNotifications();
    }
  }, [user, loadDatasets, loadNotifications]);

  useEffect(() => {
    if (user) loadFilters();
  }, [user, loadFilters]);

  useEffect(() => {
    if (user) loadAnalytics();
  }, [user, loadAnalytics]);

  const common = useMemo(() => ({
    datasets,
    selectedDatasetId,
    setSelectedDatasetId,
    analytics,
    loading,
    refresh: async () => {
      await loadDatasets();
      await loadAnalytics();
      await loadNotifications();
    }
  }), [datasets, selectedDatasetId, analytics, loading, loadDatasets, loadAnalytics, loadNotifications]);

  if (!user) return <AuthPage />;

  return (
    <Layout activePage={activePage} setActivePage={setActivePage} notifications={notifications} refreshNotifications={loadNotifications}>
      {activePage === "dashboard" && <DashboardPage {...common} filters={filters} setFilters={setFilters} datasetFilters={datasetFilters} />}
      {activePage === "upload" && <UploadPage onUploaded={async (id) => { setSelectedDatasetId(String(id)); await common.refresh(); setActivePage("forecast"); }} />}
      {activePage === "forecast" && <ForecastPage {...common} />}
      {activePage === "reports" && <ReportsPage {...common} />}
      {activePage === "admin" && <AdminPage />}
    </Layout>
  );
}
