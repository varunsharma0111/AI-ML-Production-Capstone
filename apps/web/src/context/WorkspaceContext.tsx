import React, { createContext, useContext, useState } from "react";
import { Permission, Workspace, WorkspaceRole } from "../types/api";

interface WorkspaceContextType {
  activeWorkspace: Workspace;
  availableWorkspaces: Workspace[];
  setActiveWorkspace: (workspace: Workspace) => void;
  hasPermission: (permission: Permission) => boolean;
}

const DEFAULT_WORKSPACES: Workspace[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    slug: "engineering",
    name: "Engineering Workspace (Owner)",
    role: "owner",
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    slug: "ml-research",
    name: "ML Research Workspace (Editor)",
    role: "editor",
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    slug: "auditors",
    name: "Audit Workspace (Viewer)",
    role: "viewer",
  },
];

const ROLE_PERMISSIONS: Record<WorkspaceRole, Set<Permission>> = {
  owner: new Set<Permission>([
    "workspace:read",
    "task:create",
    "task:read",
    "task:update",
    "dataset:create",
    "dataset:read",
  ]),
  editor: new Set<Permission>([
    "workspace:read",
    "task:create",
    "task:read",
    "task:update",
    "dataset:create",
    "dataset:read",
  ]),
  viewer: new Set<Permission>(["workspace:read", "task:read", "dataset:read"]),
};

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace>(DEFAULT_WORKSPACES[0]);

  const hasPermission = (permission: Permission): boolean => {
    const permissions = ROLE_PERMISSIONS[activeWorkspace.role];
    return permissions ? permissions.has(permission) : false;
  };

  return (
    <WorkspaceContext.Provider
      value={{
        activeWorkspace,
        availableWorkspaces: DEFAULT_WORKSPACES,
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
