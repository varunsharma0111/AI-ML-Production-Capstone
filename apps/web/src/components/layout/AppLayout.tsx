import React, { useEffect, useState } from "react";
import { useWorkspace } from "../../context/WorkspaceContext";
import { AgentWorkspace } from "../agent/AgentWorkspace";
import { AuditLogViewer } from "../audit/AuditLogViewer";
import { DatasetList } from "../datasets/DatasetList";
import { InferenceSandbox } from "../inference/InferenceSandbox";
import { PredictionHistory } from "../inference/PredictionHistory";
import { ModelComparisonView } from "../models/ModelComparisonView";
import { ModelRegistryList } from "../models/ModelRegistryList";
import { OperationsDashboard } from "../operations/OperationsDashboard";
import { TaskList } from "../tasks/TaskList";
import { TrainingFormModal } from "../training/TrainingFormModal";
import { TrainingJobList } from "../training/TrainingJobList";
import {
  IconBot,
  IconBox,
  IconChevronRight,
  IconCpu,
  IconDashboard,
  IconDatabase,
  IconGitCompare,
  IconHistory,
  IconListTodo,
  IconShield,
  IconZap,
} from "../ui/Icons";
import { Header } from "./Header";

export type NavSection =
  | "overview"
  | "datasets"
  | "training"
  | "models"
  | "compare"
  | "sandbox"
  | "predictions"
  | "agent"
  | "tasks"
  | "audit";

const VALID_SECTIONS: NavSection[] = [
  "overview",
  "datasets",
  "training",
  "models",
  "compare",
  "sandbox",
  "predictions",
  "agent",
  "tasks",
  "audit",
];

interface NavItemDef {
  id: NavSection;
  label: string;
  icon: React.ReactNode;
}

interface NavGroupDef {
  title: string;
  items: NavItemDef[];
}

export const AppLayout: React.FC = () => {
  const { activeWorkspace } = useWorkspace();

  const getInitialSection = (): NavSection => {
    const hash = window.location.hash.replace("#", "").toLowerCase() as NavSection;
    return VALID_SECTIONS.includes(hash) ? hash : "overview";
  };

  const [activeSection, setActiveSection] = useState<NavSection>(getInitialSection);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);

  const [selectedSandboxModelId, setSelectedSandboxModelId] = useState<string | undefined>(undefined);
  const [isTrainModalOpen, setIsTrainModalOpen] = useState<boolean>(false);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  const navigateToSection = (section: NavSection) => {
    setActiveSection(section);
    window.location.hash = section;
    setIsMobileMenuOpen(false);
  };

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace("#", "").toLowerCase() as NavSection;
      if (VALID_SECTIONS.includes(hash)) {
        setActiveSection(hash);
      }
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const handleJobSubmitted = () => {
    navigateToSection("training");
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleOpenSandbox = (modelId: string) => {
    setSelectedSandboxModelId(modelId);
    navigateToSection("sandbox");
  };

  const navGroups: NavGroupDef[] = [
    {
      title: "PLATFORM",
      items: [
        { id: "overview", label: "Overview", icon: <IconDashboard size={17} /> },
        { id: "datasets", label: "Datasets", icon: <IconDatabase size={17} /> },
        { id: "training", label: "Model Training", icon: <IconCpu size={17} /> },
        { id: "models", label: "Model Registry", icon: <IconBox size={17} /> },
        { id: "sandbox", label: "Inference Sandbox", icon: <IconZap size={17} /> },
      ],
    },
    {
      title: "ANALYSIS & INSIGHTS",
      items: [
        { id: "compare", label: "Model Comparison", icon: <IconGitCompare size={17} /> },
        { id: "predictions", label: "Prediction History", icon: <IconHistory size={17} /> },
        { id: "agent", label: "AI Platform Assistant", icon: <IconBot size={17} /> },
      ],
    },
    {
      title: "GOVERNANCE & OPS",
      items: [
        { id: "tasks", label: "Tasks & Jobs", icon: <IconListTodo size={17} /> },
        { id: "audit", label: "Audit Logs", icon: <IconShield size={17} /> },
      ],
    },
  ];

  const allItems = navGroups.flatMap((g) => g.items);
  const currentNavItem = allItems.find((n) => n.id === activeSection) || allItems[0];

  return (
    <div className="aura-shell">
      <Header
        onNavigateHome={() => navigateToSection("overview")}
        onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
      />

      <div style={{ display: "flex", flex: 1, position: "relative" }}>
        {/* Left Sidebar Navigation */}
        <aside
          aria-label="Main Platform Sidebar Navigation"
          className={`aura-sidebar ${isMobileMenuOpen ? "mobile-open" : ""}`}
        >
          <div style={{ padding: "1.25rem 0.75rem 0.5rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            {navGroups.map((group) => (
              <div key={group.title} style={{ marginBottom: "0.5rem" }}>
                <div className="nav-group-label">{group.title}</div>
                {group.items.map((item) => {
                  const isActive = activeSection === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => navigateToSection(item.id)}
                      aria-current={isActive ? "page" : undefined}
                      className={`nav-item-btn ${isActive ? "active" : ""}`}
                    >
                      {item.icon}
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          <div
            style={{
              marginTop: "auto",
              padding: "1rem 1.25rem",
              borderTop: "1px solid var(--border-subtle)",
              fontSize: "0.71875rem",
              color: "var(--text-muted)",
              display: "flex",
              flexDirection: "column",
              gap: "0.25rem",
            }}
          >
            <div style={{ fontWeight: 600, color: "var(--text-secondary)" }}>AuraML Production v2.4</div>
            <div>PostgreSQL • OIDC • Redis Workers</div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="aura-main">
          {/* Breadcrumb Header */}
          <nav aria-label="Breadcrumb Navigation" style={{ marginBottom: "1.5rem" }}>
            <ol
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                listStyle: "none",
                padding: 0,
                margin: 0,
                fontSize: "0.8125rem",
                color: "var(--text-muted)",
              }}
            >
              <li>
                <button
                  onClick={() => navigateToSection("overview")}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: 0,
                    fontSize: "0.8125rem",
                  }}
                >
                  AuraML Platform
                </button>
              </li>
              <li>
                <IconChevronRight size={14} />
              </li>
              <li style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
                {activeWorkspace.name}
              </li>
              <li>
                <IconChevronRight size={14} />
              </li>
              <li style={{ color: "var(--accent-blue)", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.35rem" }}>
                {currentNavItem.icon}
                <span>{currentNavItem.label}</span>
              </li>
            </ol>
          </nav>

          {/* Section Renderers */}
          {activeSection === "overview" && <OperationsDashboard />}
          {activeSection === "datasets" && <DatasetList />}
          {activeSection === "training" && (
            <TrainingJobList
              onOpenTrainModal={() => setIsTrainModalOpen(true)}
              refreshTrigger={refreshTrigger}
            />
          )}
          {activeSection === "models" && <ModelRegistryList onRunInference={handleOpenSandbox} />}
          {activeSection === "compare" && <ModelComparisonView />}
          {activeSection === "sandbox" && <InferenceSandbox initialModelId={selectedSandboxModelId} />}
          {activeSection === "predictions" && <PredictionHistory />}
          {activeSection === "agent" && <AgentWorkspace />}
          {activeSection === "tasks" && <TaskList />}
          {activeSection === "audit" && <AuditLogViewer />}

          <TrainingFormModal
            isOpen={isTrainModalOpen}
            onClose={() => setIsTrainModalOpen(false)}
            onJobSubmitted={handleJobSubmitted}
          />
        </main>
      </div>
    </div>
  );
};
