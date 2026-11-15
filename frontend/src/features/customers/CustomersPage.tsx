
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  Users,
  Plus,
  Search,
  Pencil,
  Trash2,
  X,
  LoaderCircle,
  AlertCircle,
  Building2,
  Mail,
  Phone,
} from "lucide-react";
import api from "../../lib/api";
import type { Customer } from "../conversations/types";
import "./Customers.css";

interface CustomerForm {
  full_name: string;
  email: string;
  phone: string;
  company: string;
}

const emptyForm: CustomerForm = {
  full_name: "",
  email: "",
  phone: "",
  company: "",
};

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [form, setForm] = useState<CustomerForm>(emptyForm);

  const loadCustomers = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const { data } = await api.get<Customer[]>("/customers", {
        params: { skip: 0, limit: 100 },
      });
      setCustomers(data);
    } catch {
      setError("Unable to load customers. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCustomers();
  }, [loadCustomers]);

  const filteredCustomers = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) return customers;

    return customers.filter((customer) =>
      [
        customer.full_name,
        customer.email,
        customer.phone ?? "",
        customer.company ?? "",
      ].some((value) => value.toLowerCase().includes(query)),
    );
  }, [customers, search]);

  const openCreateModal = () => {
    setEditingCustomer(null);
    setForm(emptyForm);
    setError("");
    setModalOpen(true);
  };

  const openEditModal = (customer: Customer) => {
    setEditingCustomer(customer);
    setForm({
      full_name: customer.full_name,
      email: customer.email,
      phone: customer.phone ?? "",
      company: customer.company ?? "",
    });
    setError("");
    setModalOpen(true);
  };

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setEditingCustomer(null);
    setForm(emptyForm);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");

    const payload = {
      full_name: form.full_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
      company: form.company.trim() || null,
    };

    try {
      if (editingCustomer) {
        await api.patch(`/customers/${editingCustomer.id}`, payload);
      } else {
        await api.post("/customers", payload);
      }

      setModalOpen(false);
      setEditingCustomer(null);
      setForm(emptyForm);
      await loadCustomers();
    } catch (err: unknown) {
      const message =
        typeof err === "object" &&
        err !== null &&
        "response" in err
          ? (err as { response?: { data?: { detail?: string } } })
              .response?.data?.detail
          : undefined;

      setError(
        typeof message === "string"
          ? message
          : "Unable to save customer. Please check the details and try again.",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (customer: Customer) => {
    const confirmed = window.confirm(
      `Delete customer "${customer.full_name}"? This action cannot be undone.`,
    );

    if (!confirmed) return;

    setError("");

    try {
      await api.delete(`/customers/${customer.id}`);
      setCustomers((current) =>
        current.filter((item) => item.id !== customer.id),
      );
    } catch {
      setError("Unable to delete this customer. Please try again.");
    }
  };

  return (
    <section className="customers-page">
      <header className="customers-heading">
        <div>
          <div className="customers-eyebrow">
            <Users size={14} />
            CUSTOMER RELATIONSHIPS
          </div>
          <h1>Customers</h1>
          <p>Manage your customer records and contact information.</p>
        </div>

        <button
          type="button"
          className="customer-add-button"
          onClick={openCreateModal}
        >
          <Plus size={17} />
          Add customer
        </button>
      </header>

      <div className="customers-stats">
        <div className="customer-stat-icon">
          <Users size={21} />
        </div>
        <div>
          <span>Total customers</span>
          <strong>{customers.length}</strong>
        </div>
      </div>

      <div className="customers-panel">
        <div className="customers-toolbar">
          <div>
            <h2>All customers</h2>
            <p>{filteredCustomers.length} records</p>
          </div>

          <div className="customers-search">
            <Search size={17} />
            <input
              type="search"
              placeholder="Search customers..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        {error && !modalOpen && (
          <div className="customers-error">
            <AlertCircle size={18} />
            {error}
            <button onClick={() => void loadCustomers()}>Retry</button>
          </div>
        )}

        {loading ? (
          <div className="customers-state">
            <LoaderCircle className="sf-spin" size={26} />
            <span>Loading customers...</span>
          </div>
        ) : filteredCustomers.length === 0 ? (
          <div className="customers-empty">
            <div className="customers-empty-icon">
              <Users size={28} />
            </div>
            <h3>{search ? "No matching customers" : "No customers yet"}</h3>
            <p>
              {search
                ? "Try another name, email, phone number or company."
                : "Add your first customer to start managing conversations."}
            </p>
            {!search && (
              <button onClick={openCreateModal}>
                <Plus size={16} />
                Add your first customer
              </button>
            )}
          </div>
        ) : (
          <div className="customers-table-wrap">
            <table className="customers-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Company</th>
                  <th>Phone</th>
                  <th>Status</th>
                  <th className="customer-actions-heading">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredCustomers.map((customer) => (
                  <tr key={customer.id}>
                    <td>
                      <div className="customer-identity">
                        <div className="customer-avatar">
                          {customer.full_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <strong>{customer.full_name}</strong>
                          <span>{customer.email}</span>
                        </div>
                      </div>
                    </td>
                    <td>{customer.company || "—"}</td>
                    <td>{customer.phone || "—"}</td>
                    <td>
                      <span
                        className={`customer-status ${
                          customer.is_active ? "is-active" : "is-inactive"
                        }`}
                      >
                        {customer.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td>
                      <div className="customer-row-actions">
                        <button
                          type="button"
                          title="Edit customer"
                          aria-label={`Edit ${customer.full_name}`}
                          onClick={() => openEditModal(customer)}
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          type="button"
                          title="Delete customer"
                          aria-label={`Delete ${customer.full_name}`}
                          className="customer-delete-action"
                          onClick={() => void handleDelete(customer)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modalOpen && (
        <div className="customer-modal-overlay" onClick={closeModal}>
          <div
            className="customer-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="customer-modal-header">
              <div>
                <h2>{editingCustomer ? "Edit customer" : "Add customer"}</h2>
                <p>
                  {editingCustomer
                    ? "Update this customer's contact information."
                    : "Add a customer to your organization."}
                </p>
              </div>
              <button
                type="button"
                onClick={closeModal}
                disabled={saving}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </header>

            <form onSubmit={handleSubmit}>
              <div className="customer-modal-body">
                <label>
                  Full name <span>*</span>
                  <div className="customer-input-wrap">
                    <Users size={16} />
                    <input
                      required
                      minLength={1}
                      maxLength={150}
                      value={form.full_name}
                      onChange={(event) =>
                        setForm({ ...form, full_name: event.target.value })
                      }
                      placeholder="Enter full name"
                    />
                  </div>
                </label>

                <label>
                  Email address <span>*</span>
                  <div className="customer-input-wrap">
                    <Mail size={16} />
                    <input
                      required
                      type="email"
                      maxLength={255}
                      value={form.email}
                      onChange={(event) =>
                        setForm({ ...form, email: event.target.value })
                      }
                      placeholder="customer@example.com"
                    />
                  </div>
                </label>

                <label>
                  Phone number
                  <div className="customer-input-wrap">
                    <Phone size={16} />
                    <input
                      type="tel"
                      maxLength={30}
                      value={form.phone}
                      onChange={(event) =>
                        setForm({ ...form, phone: event.target.value })
                      }
                      placeholder="+92 300 1234567"
                    />
                  </div>
                </label>

                <label>
                  Company
                  <div className="customer-input-wrap">
                    <Building2 size={16} />
                    <input
                      maxLength={150}
                      value={form.company}
                      onChange={(event) =>
                        setForm({ ...form, company: event.target.value })
                      }
                      placeholder="Company name"
                    />
                  </div>
                </label>

                {error && (
                  <div className="customers-error">
                    <AlertCircle size={17} />
                    {error}
                  </div>
                )}
              </div>

              <footer className="customer-modal-footer">
                <button
                  type="button"
                  className="customer-cancel-button"
                  onClick={closeModal}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="customer-save-button"
                  disabled={saving}
                >
                  {saving ? (
                    <>
                      <LoaderCircle size={16} className="sf-spin" />
                      Saving...
                    </>
                  ) : editingCustomer ? (
                    "Save changes"
                  ) : (
                    "Create customer"
                  )}
                </button>
              </footer>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
