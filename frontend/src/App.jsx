import React, { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import api from "./api/client";
import Layout from "./components/Layout";
import { useAuth } from "./state/AuthContext";
import AuthPage from "./views/AuthPage";

const AdminPage = lazy(() => import("./views/AdminPage"));
const AutomationPage = lazy(() => import("./views/AutomationPage"));
const AccuracyCenterPage = lazy(() => import("./views/AccuracyCenterPage"));
const CollaborationPage = lazy(() => import("./views/CollaborationPage"));
const ExecutiveDashboardPage = lazy(() => import("./views/ExecutiveDashboardPage"));
const ScenarioPlannerPage = lazy(() => import("./views/ScenarioPlannerPage"));
const WorkspacesPage = lazy(() => import("./views/WorkspacesPage"));
const IntegrationsPage = lazy(() => import("./views/IntegrationsPage"));
const SettingsPage = lazy(() => import("./views/SettingsPage"));
const DashboardPage = lazy(() => import("./views/DashboardPage"));
const ForecastPage = lazy(() => import("./views/ForecastPage"));
const InsightsPage = lazy(() => import("./views/InsightsPage"));
const ReportsPage = lazy(() => import("./views/ReportsPage"));
const UploadPage = lazy(() => import("./views/UploadPage"));
const OrganizationsPage = lazy(() => import("./views/OrganizationsPage"));
const ApprovalsPage = lazy(() => import("./views/ApprovalsPage"));
const EnterprisePlanningPage = lazy(() => import("./views/EnterprisePlanningPage"));
const GovernanceCenterPage = lazy(() => import("./views/GovernanceCenterPage"));
const QualityKpiPage = lazy(() => import("./views/QualityKpiPage"));
const CommandCenterPage = lazy(() => import("./views/CommandCenterPage"));
const NotificationCenterPage = lazy(() => import("./views/NotificationCenterPage"));

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
  const [advancedAnalytics, setAdvancedAnalytics] = useState(null);
  const [liveSnapshot, setLiveSnapshot] = useState(null);
  const [liveMode, setLiveMode] = useState(true);
  const [autoForecast, setAutoForecast] = useState(false);

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
      const [basic, advanced, live] = await Promise.all([
        api.get(`/analytics/${selectedDatasetId}?${params.toString()}`),
        api.get(`/analytics/${selectedDatasetId}/advanced`),
        api.get(`/realtime/${selectedDatasetId}/snapshot`)
      ]);
      setAnalytics(basic.data);
      setAdvancedAnalytics(advanced.data);
      setLiveSnapshot(live.data);
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

  useEffect(() => {
    if (!user || !selectedDatasetId || !liveMode) return undefined;
    const timer = setInterval(() => {
      loadAnalytics();
      loadNotifications();
    }, 15000);
    return () => clearInterval(timer);
  }, [user, selectedDatasetId, liveMode, loadAnalytics, loadNotifications]);

  useEffect(() => {
    if (!user || user.role === "viewer" || !selectedDatasetId || !autoForecast) return undefined;
    const timer = setInterval(async () => {
      await api.post(`/realtime/${selectedDatasetId}/auto-refresh?periods=6`);
      await loadAnalytics();
      await loadNotifications();
    }, 60000);
    return () => clearInterval(timer);
  }, [user, selectedDatasetId, autoForecast, loadAnalytics, loadNotifications]);

  const common = useMemo(() => ({
    datasets,
    selectedDatasetId,
    setSelectedDatasetId,
    analytics,
    advancedAnalytics,
    liveSnapshot,
    liveMode,
    setLiveMode,
    autoForecast,
    setAutoForecast,
    canOperate: user?.role !== "viewer",
    loading,
    refresh: async () => {
      await loadDatasets();
      await loadAnalytics();
      await loadNotifications();
    }
  }), [datasets, selectedDatasetId, analytics, advancedAnalytics, liveSnapshot, liveMode, autoForecast, loading, user?.role, loadDatasets, loadAnalytics, loadNotifications]);

  if (!user) return <AuthPage />;

  return (
    <Layout activePage={activePage} setActivePage={setActivePage} notifications={notifications} refreshNotifications={loadNotifications}>
      <Suspense fallback={<div className="panel animate-pulse">Loading workspace module...</div>}>
        {activePage === "dashboard" && <DashboardPage {...common} filters={filters} setFilters={setFilters} datasetFilters={datasetFilters} onNavigate={setActivePage} />}
        {activePage === "workspaces" && <WorkspacesPage {...common} />}
        {activePage === "executive" && <ExecutiveDashboardPage {...common} />}
        {activePage === "scenarios" && <ScenarioPlannerPage {...common} />}
        {activePage === "collaboration" && <CollaborationPage {...common} />}
        {activePage === "accuracy" && <AccuracyCenterPage {...common} />}
        {activePage === "insights" && <InsightsPage {...common} />}
        {activePage === "upload" && <UploadPage onUploaded={async (id) => { setSelectedDatasetId(String(id)); await common.refresh(); setActivePage("forecast"); }} />}
        {activePage === "forecast" && <ForecastPage {...common} />}
        {activePage === "reports" && <ReportsPage {...common} />}
        {activePage === "automation" && <AutomationPage {...common} />}
        {activePage === "integrations" && <IntegrationsPage {...common} />}
        {activePage === "settings" && <SettingsPage {...common} />}
        {activePage === "organizations" && <OrganizationsPage {...common} />}
        {activePage === "approvals" && <ApprovalsPage {...common} />}
        {activePage === "enterprise-planning" && <EnterprisePlanningPage {...common} />}
        {activePage === "governance" && <GovernanceCenterPage {...common} />}
        {activePage === "quality-kpi" && <QualityKpiPage {...common} />}
        {activePage === "command-center" && <CommandCenterPage {...common} />}
        {activePage === "notification-center" && <NotificationCenterPage {...common} />}
        {activePage === "admin" && <AdminPage />}
      </Suspense>
    </Layout>
  );
}





