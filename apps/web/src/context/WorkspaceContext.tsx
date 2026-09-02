import React, { createContext, useContext, useEffect, useState } from "react";
import { Permission, Workspace } from "../types/api";
import { useAuth } from "./AuthContext";

interface WorkspaceContextType {
  activeWorkspace: Workspace;
  availableWorkspaces: Workspace[];
  setActiveWorkspace: (workspace: Workspace) => void;
  hasPermission: (permission: Permission) => boolean;
}

const STORAGE_KEY = "auraml_selected_workspace_id";

const DEFAULT_DEV_WORKSPACE: Workspace = {
  id: "00000000-0000-4000-a000-000000000001",
  slug: "public-test-workspace",
  name: "Public Test Workspace",
  role: "owner",
};

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const availableWorkspaces = (user?.workspaces && user.workspaces.length > 0) ? user.workspaces : [DEFAULT_DEV_WORKSPACE];

  const [activeWorkspaceState, setActiveWorkspaceState] = useState<Workspace>(DEFAULT_DEV_WORKSPACE);

  useEffect(() => {
    if (!availableWorkspaces || availableWorkspaces.length === 0) {
      setActiveWorkspaceState(DEFAULT_DEV_WORKSPACE);
      return;
    }

    const storedId = localStorage.getItem(STORAGE_KEY);
    const validStoredWorkspace = storedId
      ? availableWorkspaces.find((w) => w.id === storedId)
      : null;

    if (validStoredWorkspace) {
      setActiveWorkspaceState(validStoredWorkspace);
    } else {
      const defaultWs = availableWorkspaces[0] || DEFAULT_DEV_WORKSPACE;
      setActiveWorkspaceState(defaultWs);
      localStorage.setItem(STORAGE_KEY, defaultWs.id);
    }
  }, [user?.id, JSON.stringify(availableWorkspaces)]);

  const setActiveWorkspace = (workspace: Workspace) => {
    setActiveWorkspaceState(workspace);
    localStorage.setItem(STORAGE_KEY, workspace.id);
  };

  const hasPermission = (_permission: Permission): boolean => {
    // Role permissions bypassed for local website testing
    return true;
  };

  return (
    <WorkspaceContext.Provider
      value={{
        activeWorkspace: activeWorkspaceState,
        availableWorkspaces,
        setActiveWorkspace,
        hasPermission,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = (): WorkspaceContextType => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return context;
};
