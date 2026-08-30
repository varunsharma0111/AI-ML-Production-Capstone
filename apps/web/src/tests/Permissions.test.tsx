import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "../context/AuthContext";
import { WorkspaceProvider, useWorkspace } from "../context/WorkspaceContext";

const PermissionTester: React.FC = () => {
  const { hasPermission, activeWorkspace } = useWorkspace();
  const canCreate = hasPermission("task:create");
  const canUpdate = hasPermission("task:update");

  return (
    <div>
      <span data-testid="role">{activeWorkspace.role}</span>
      <span data-testid="can-create">{canCreate ? "yes" : "no"}</span>
      <span data-testid="can-update">{canUpdate ? "yes" : "no"}</span>
    </div>
  );
};

describe("WorkspaceContext RBAC Permissions", () => {
  it("grants task creation and update permissions to default owner role", () => {
    render(
      <AuthProvider>
        <WorkspaceProvider>
          <PermissionTester />
        </WorkspaceProvider>
      </AuthProvider>
    );

    expect(screen.getByTestId("role")).toHaveTextContent("owner");
    expect(screen.getByTestId("can-create")).toHaveTextContent("yes");
    expect(screen.getByTestId("can-update")).toHaveTextContent("yes");
  });
});
