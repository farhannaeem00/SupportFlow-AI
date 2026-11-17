import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  AlertCircle,
  LoaderCircle,
  Mail,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  Users,
  X,
} from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { teamApi } from "./teamApi";
import type { CreateTeamMemberPayload, TeamMember, TeamRole } from "./types";
import "./Team.css";

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join(", ");
    }

    if (typeof error.response?.data?.message === "string") {
      return error.response.data.message;
    }

    if (error.response?.status === 403) {
      return "You do not have permission to perform this action.";
    }

    return error.message || "A network error occurred. Please try again.";
  }

  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}

const initialForm: CreateTeamMemberPayload = {
  full_name: "",
  email: "",
  password: "",
  role: "agent",
};

export default function TeamPage() {
  const { organization, organizations } = useAuth();

  const currentMembership = organizations.find(
    (item) => item.id === organization?.id,
  );
  const canManage = currentMembership?.role?.toLowerCase() === "owner";

  const [members, setMembers] = useState<TeamMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pageError, setPageError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [search, setSearch] = useState("");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState<CreateTeamMemberPayload>(initialForm);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [busyMemberId, setBusyMemberId] = useState<string | null>(null);

  const loadMembers = useCallback(async (refresh = false) => {
    if (refresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    setPageError("");

    try {
      const data = await teamApi.getMembers();
      setMembers(data);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadMembers();
  }, [loadMembers]);

  const filteredMembers = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) return members;

    return members.filter(
      (member) =>
        member.full_name.toLowerCase().includes(query) ||
        member.email.toLowerCase().includes(query) ||
        member.role.toLowerCase().includes(query),
    );
  }, [members, search]);

  const ownerCount = members.filter(
    (member) => member.role === "owner",
  ).length;

  function openCreateModal() {
    setForm(initialForm);
    setFormError("");
    setSuccessMessage("");
    setIsModalOpen(true);
  }

  function closeCreateModal() {
    if (isSubmitting) return;

    setIsModalOpen(false);
    setForm(initialForm);
    setFormError("");
  }

  async function handleCreateMember(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    setSuccessMessage("");

    if (form.full_name.trim().length < 2) {
      setFormError("Full name must contain at least 2 characters.");
      return;
    }

    if (form.password.length < 8) {
      setFormError("Password must contain at least 8 characters.");
      return;
    }

    setIsSubmitting(true);

    try {
      await teamApi.createMember({
        ...form,
        full_name: form.full_name.trim(),
        email: form.email.trim().toLowerCase(),
      });

      setIsModalOpen(false);
      setForm(initialForm);
      setSuccessMessage("Team member account created successfully.");
      await loadMembers(true);
    } catch (error) {
      setFormError(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRoleChange(
    member: TeamMember,
    newRole: TeamRole,
  ) {
    if (member.role === newRole) return;

    const confirmed = window.confirm(
      `Change ${member.full_name}'s role from ${member.role} to ${newRole}?`,
    );

    if (!confirmed) return;

    setBusyMemberId(member.id);
    setPageError("");
    setSuccessMessage("");

    try {
      await teamApi.updateMemberRole(member.id, { role: newRole });
      setSuccessMessage(`${member.full_name}'s role was updated.`);
      await loadMembers(true);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setBusyMemberId(null);
    }
  }

  async function handleRemoveMember(member: TeamMember) {
    const confirmed = window.confirm(
      `Remove ${member.full_name} (${member.email}) from this organization? This action cannot be undone.`,
    );

    if (!confirmed) return;

    setBusyMemberId(member.id);
    setPageError("");
    setSuccessMessage("");

    try {
      await teamApi.removeMember(member.id);
      setSuccessMessage(`${member.full_name} was removed from the team.`);
      await loadMembers(true);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setBusyMemberId(null);
    }
  }

  return (
    <div className="team-page">
      <div className="team-page-header">
        <div>
          <div className="team-eyebrow">
            <Users size={15} />
            WORKSPACE MANAGEMENT
          </div>
          <h1>Team Members</h1>
          <p>
            Manage the people who have access to your organization.
          </p>
        </div>

        <div className="team-header-actions">
          <button
            type="button"
            className="team-secondary-button"
            onClick={() => void loadMembers(true)}
            disabled={isLoading || isRefreshing}
          >
            <RefreshCw
              size={16}
              className={isRefreshing ? "team-spin" : ""}
            />
            Refresh
          </button>

          {canManage && (
            <button
              type="button"
              className="team-primary-button"
              onClick={openCreateModal}
            >
              <Plus size={17} />
              Add team member
            </button>
          )}
        </div>
      </div>

      {pageError && (
        <div className="team-alert team-alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{pageError}</span>
          <button
            type="button"
            aria-label="Dismiss error"
            onClick={() => setPageError("")}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {successMessage && (
        <div className="team-alert team-alert-success" role="status">
          <ShieldCheck size={18} />
          <span>{successMessage}</span>
          <button
            type="button"
            aria-label="Dismiss message"
            onClick={() => setSuccessMessage("")}
          >
            <X size={16} />
          </button>
        </div>
      )}

      <div className="team-stats-grid">
        <div className="team-stat-card">
          <div className="team-stat-icon">
            <Users size={19} />
          </div>
          <div>
            <span>Total members</span>
            <strong>{isLoading ? "—" : members.length}</strong>
          </div>
        </div>

        <div className="team-stat-card">
          <div className="team-stat-icon team-owner-icon">
            <ShieldCheck size={19} />
          </div>
          <div>
            <span>Owners</span>
            <strong>{isLoading ? "—" : ownerCount}</strong>
          </div>
        </div>

        <div className="team-stat-card">
          <div className="team-stat-icon team-agent-icon">
            <Users size={19} />
          </div>
          <div>
            <span>Agents</span>
            <strong>
              {isLoading
                ? "—"
                : members.filter((member) => member.role === "agent").length}
            </strong>
          </div>
        </div>
      </div>

      <section className="team-content-card">
        <div className="team-content-heading">
          <div>
            <h2>Organization members</h2>
            <p>
              {members.length}{" "}
              {members.length === 1 ? "member" : "members"} in this workspace
            </p>
          </div>

          <div className="team-search">
            <Search size={17} />
            <input
              type="search"
              placeholder="Search members..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search team members"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="team-state">
            <LoaderCircle size={25} className="team-spin" />
            <p>Loading team members...</p>
          </div>
        ) : members.length === 0 ? (
          <div className="team-state">
            <div className="team-empty-icon">
              <Users size={25} />
            </div>
            <h3>No team members yet</h3>
            <p>
              Team members will appear here when they have access to this
              organization.
            </p>
            {canManage && (
              <button
                type="button"
                className="team-primary-button"
                onClick={openCreateModal}
              >
                <Plus size={17} />
                Add your first member
              </button>
            )}
          </div>
        ) : filteredMembers.length === 0 ? (
          <div className="team-state team-compact-state">
            <Search size={23} />
            <p>No members match “{search}”.</p>
          </div>
        ) : (
          <div className="team-table-wrap">
            <table className="team-table">
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Role</th>
                  <th>Status</th>
                  {canManage && <th className="team-actions-heading">Actions</th>}
                </tr>
              </thead>

              <tbody>
                {filteredMembers.map((member) => {
                  const isBusy = busyMemberId === member.id;

                  return (
                    <tr key={member.id}>
                      <td>
                        <div className="team-member-cell">
                          <div className="team-avatar">
                            {member.full_name
                              .trim()
                              .charAt(0)
                              .toUpperCase()}
                          </div>
                          <div className="team-member-info">
                            <strong>{member.full_name}</strong>
                            <span>
                              <Mail size={13} />
                              {member.email}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td>
                        {canManage ? (
                          <select
                            className="team-role-select"
                            value={member.role}
                            disabled={isBusy}
                            aria-label={`Role for ${member.full_name}`}
                            onChange={(event) =>
                              void handleRoleChange(
                                member,
                                event.target.value as TeamRole,
                              )
                            }
                          >
                            <option value="owner">Owner</option>
                            <option value="agent">Agent</option>
                          </select>
                        ) : (
                          <span
                            className={`team-role-badge team-role-${member.role}`}
                          >
                            {member.role}
                          </span>
                        )}
                      </td>

                      <td>
                        <span
                          className={`team-status ${
                            member.is_active ? "is-active" : "is-inactive"
                          }`}
                        >
                          <span />
                          {member.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>

                      {canManage && (
                        <td className="team-actions-cell">
                          <button
                            type="button"
                            className="team-remove-button"
                            title={`Remove ${member.full_name}`}
                            aria-label={`Remove ${member.full_name}`}
                            disabled={isBusy}
                            onClick={() => void handleRemoveMember(member)}
                          >
                            {isBusy ? (
                              <LoaderCircle
                                size={16}
                                className="team-spin"
                              />
                            ) : (
                              <Trash2 size={16} />
                            )}
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {!canManage && (
        <p className="team-permission-note">
          <ShieldCheck size={15} />
          Only organization owners can add, change, or remove team members.
        </p>
      )}

      {isModalOpen && (
        <div
          className="team-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeCreateModal();
            }
          }}
        >
          <section
            className="team-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="team-modal-title"
          >
            <div className="team-modal-header">
              <div>
                <span className="team-modal-eyebrow">TEAM MANAGEMENT</span>
                <h2 id="team-modal-title">Add team member</h2>
                <p>Create an account and add it to this organization.</p>
              </div>

              <button
                type="button"
                className="team-modal-close"
                onClick={closeCreateModal}
                disabled={isSubmitting}
                aria-label="Close dialog"
              >
                <X size={19} />
              </button>
            </div>

            <form onSubmit={handleCreateMember}>
              {formError && (
                <div className="team-alert team-alert-error" role="alert">
                  <AlertCircle size={17} />
                  <span>{formError}</span>
                </div>
              )}

              <label className="team-form-field">
                <span>Full name</span>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      full_name: event.target.value,
                    }))
                  }
                  placeholder="Enter full name"
                  minLength={2}
                  maxLength={150}
                  autoComplete="name"
                  required
                />
              </label>

              <label className="team-form-field">
                <span>Email address</span>
                <input
                  type="email"
                  value={form.email}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      email: event.target.value,
                    }))
                  }
                  placeholder="name@company.com"
                  autoComplete="email"
                  required
                />
              </label>

              <label className="team-form-field">
                <span>Temporary password</span>
                <input
                  type="password"
                  value={form.password}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      password: event.target.value,
                    }))
                  }
                  placeholder="At least 8 characters"
                  minLength={8}
                  maxLength={128}
                  autoComplete="new-password"
                  required
                />
                <small>
                  Share the login credentials securely with the new member.
                </small>
              </label>

              <label className="team-form-field">
                <span>Role</span>
                <select
                  value={form.role}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      role: event.target.value as TeamRole,
                    }))
                  }
                >
                  <option value="agent">Agent</option>
                  <option value="owner">Owner</option>
                </select>
              </label>

              <div className="team-modal-footer">
                <button
                  type="button"
                  className="team-secondary-button"
                  onClick={closeCreateModal}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="team-primary-button"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <LoaderCircle size={16} className="team-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus size={17} />
                      Create account
                    </>
                  )}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}