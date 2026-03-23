import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "./test-utils";

// ─── Dynamic mock for usePermissions ────────────────────────────────────────

const mockPermissions = vi.fn();

vi.mock("@/hooks/use-permissions", () => ({
  usePermissions: (...args: unknown[]) => mockPermissions(...args),
}));

vi.mock("@/hooks/use-queries", () => ({
  useCurrentUser: vi.fn(() => ({
    data: { user_id: "user-1", email: "admin@example.com" },
    isLoading: false,
  })),
  useStakeholders: vi.fn(() => ({
    data: { data: [{ email: "admin@example.com", role: "matter_admin" }] },
    isLoading: false,
  })),
}));

// ─── Import ─────────────────────────────────────────────────────────────────

import {
  RequirePermission,
  RoleGate,
} from "@/components/layout/RequirePermission";

// ─── RequirePermission Tests ────────────────────────────────────────────────

describe("RequirePermission", () => {
  it("renders children when permission is granted", () => {
    mockPermissions.mockReturnValue({
      can: () => true,
      isLoading: false,
      role: "matter_admin",
    });

    renderWithProviders(
      <RequirePermission permission="task:write" matterId="matter-1">
        <button>Edit Task</button>
      </RequirePermission>,
    );

    expect(screen.getByText("Edit Task")).toBeInTheDocument();
  });

  it("hides children when permission is denied", () => {
    mockPermissions.mockReturnValue({
      can: () => false,
      isLoading: false,
      role: "beneficiary",
    });

    renderWithProviders(
      <RequirePermission permission="task:write" matterId="matter-1">
        <button>Edit Task</button>
      </RequirePermission>,
    );

    expect(screen.queryByText("Edit Task")).not.toBeInTheDocument();
  });

  it("renders fallback when permission is denied", () => {
    mockPermissions.mockReturnValue({
      can: () => false,
      isLoading: false,
      role: "beneficiary",
    });

    renderWithProviders(
      <RequirePermission
        permission="task:write"
        matterId="matter-1"
        fallback={<span>No access</span>}
      >
        <button>Edit Task</button>
      </RequirePermission>,
    );

    expect(screen.queryByText("Edit Task")).not.toBeInTheDocument();
    expect(screen.getByText("No access")).toBeInTheDocument();
  });

  it("renders nothing while loading", () => {
    mockPermissions.mockReturnValue({
      can: () => true,
      isLoading: true,
      role: null,
    });

    const { container } = renderWithProviders(
      <RequirePermission permission="task:write" matterId="matter-1">
        <button>Edit Task</button>
      </RequirePermission>,
    );

    expect(screen.queryByText("Edit Task")).not.toBeInTheDocument();
    expect(container.innerHTML).toBe("");
  });

  it("checks the correct permission string", () => {
    mockPermissions.mockReturnValue({
      can: (perm: string) => perm === "stakeholder:manage",
      isLoading: false,
      role: "matter_admin",
    });

    renderWithProviders(
      <RequirePermission permission="stakeholder:manage" matterId="matter-1">
        <button>Manage</button>
      </RequirePermission>,
    );

    expect(screen.getByText("Manage")).toBeInTheDocument();
  });

  it("denies when checking wrong permission", () => {
    mockPermissions.mockReturnValue({
      can: (perm: string) => perm === "stakeholder:manage",
      isLoading: false,
      role: "matter_admin",
    });

    renderWithProviders(
      <RequirePermission permission="task:write" matterId="matter-1">
        <button>Write</button>
      </RequirePermission>,
    );

    expect(screen.queryByText("Write")).not.toBeInTheDocument();
  });

  it("passes matterId to usePermissions", () => {
    mockPermissions.mockReturnValue({
      can: () => true,
      isLoading: false,
      role: "matter_admin",
    });

    renderWithProviders(
      <RequirePermission permission="task:read" matterId="custom-matter-id">
        <span>visible</span>
      </RequirePermission>,
    );

    expect(mockPermissions).toHaveBeenCalledWith("custom-matter-id");
  });
});

// ─── RoleGate Tests ─────────────────────────────────────────────────────────

describe("RoleGate", () => {
  it("renders children when role is in allow list", () => {
    mockPermissions.mockReturnValue({
      role: "matter_admin",
      isLoading: false,
    });

    renderWithProviders(
      <RoleGate matterId="matter-1" allow={["matter_admin", "professional"]}>
        <span>Admin Content</span>
      </RoleGate>,
    );

    expect(screen.getByText("Admin Content")).toBeInTheDocument();
  });

  it("hides children when role is not in allow list", () => {
    mockPermissions.mockReturnValue({
      role: "beneficiary",
      isLoading: false,
    });

    renderWithProviders(
      <RoleGate matterId="matter-1" allow={["matter_admin", "professional"]}>
        <span>Admin Content</span>
      </RoleGate>,
    );

    expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
  });

  it("hides children when role is in deny list", () => {
    mockPermissions.mockReturnValue({
      role: "read_only",
      isLoading: false,
    });

    renderWithProviders(
      <RoleGate matterId="matter-1" deny={["read_only", "beneficiary"]}>
        <span>Secret</span>
      </RoleGate>,
    );

    expect(screen.queryByText("Secret")).not.toBeInTheDocument();
  });

  it("renders children when role is not in deny list", () => {
    mockPermissions.mockReturnValue({
      role: "professional",
      isLoading: false,
    });

    renderWithProviders(
      <RoleGate matterId="matter-1" deny={["read_only", "beneficiary"]}>
        <span>Pro Content</span>
      </RoleGate>,
    );

    expect(screen.getByText("Pro Content")).toBeInTheDocument();
  });

  it("renders fallback when denied", () => {
    mockPermissions.mockReturnValue({
      role: "beneficiary",
      isLoading: false,
    });

    renderWithProviders(
      <RoleGate
        matterId="matter-1"
        allow={["matter_admin"]}
        fallback={<span>Restricted</span>}
      >
        <span>Admin Only</span>
      </RoleGate>,
    );

    expect(screen.queryByText("Admin Only")).not.toBeInTheDocument();
    expect(screen.getByText("Restricted")).toBeInTheDocument();
  });

  it("renders nothing while loading", () => {
    mockPermissions.mockReturnValue({
      role: null,
      isLoading: true,
    });

    const { container } = renderWithProviders(
      <RoleGate matterId="matter-1" allow={["matter_admin"]}>
        <span>Content</span>
      </RoleGate>,
    );

    expect(container.innerHTML).toBe("");
  });

  it("renders fallback when role is null (no stakeholder)", () => {
    mockPermissions.mockReturnValue({
      role: null,
      isLoading: false,
    });

    renderWithProviders(
      <RoleGate
        matterId="matter-1"
        allow={["matter_admin"]}
        fallback={<span>No Role</span>}
      >
        <span>Content</span>
      </RoleGate>,
    );

    expect(screen.queryByText("Content")).not.toBeInTheDocument();
    expect(screen.getByText("No Role")).toBeInTheDocument();
  });

  it("renders for executor_trustee when allowed", () => {
    mockPermissions.mockReturnValue({
      role: "executor_trustee",
      isLoading: false,
    });

    renderWithProviders(
      <RoleGate matterId="matter-1" allow={["executor_trustee", "matter_admin"]}>
        <span>Executor View</span>
      </RoleGate>,
    );

    expect(screen.getByText("Executor View")).toBeInTheDocument();
  });
});
