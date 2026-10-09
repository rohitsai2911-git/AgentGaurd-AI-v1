"use client";

import { useEffect, useState } from "react";

import {
  Checkbox,
  Field,
  FormSection,
  TextArea,
  TextInput,
} from "@/components/fields";
import { Modal } from "@/components/modal";
import { Button } from "@/components/ui";
import { endpoints } from "@/lib/api/endpoints";
import type { TestSuite } from "@/lib/api/types";
import { parseListInput } from "@/lib/format";
import { toApiError, useResource } from "@/lib/hooks";

export function SuiteForm({
  open,
  suite,
  onClose,
  onSaved,
}: {
  open: boolean;
  suite: TestSuite | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const cases = useResource(() => endpoints.listTestCases({ limit: 200 }), [], {
    enabled: open,
  });

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(suite?.name ?? "");
    setDescription(suite?.description ?? "");
    setTags((suite?.tags ?? []).join(", "));
    setSelected(suite?.test_cases.map((ref) => ref.test_case_id) ?? []);
    setError(null);
  }, [open, suite]);

  async function submit() {
    setError(null);
    if (name.trim().length < 3) {
      setError("Suite name must be at least 3 characters.");
      return;
    }
    setPending(true);
    try {
      if (suite) {
        await endpoints.updateSuite(suite.id, {
          name: name.trim(),
          description,
          tags: parseListInput(tags),
        });
        const existing = new Set(
          suite.test_cases.map((ref) => ref.test_case_id),
        );
        const toAdd = selected.filter((id) => !existing.has(id));
        if (toAdd.length > 0) {
          await endpoints.addSuiteTestCases(suite.id, toAdd);
        }
        for (const id of existing) {
          if (!selected.includes(id)) {
            await endpoints.removeSuiteTestCase(suite.id, id);
          }
        }
      } else {
        await endpoints.createSuite({
          name: name.trim(),
          description,
          tags: parseListInput(tags),
          test_case_ids: selected,
        });
      }
      onSaved();
    } catch (caught) {
      setError(toApiError(caught).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={suite ? "Edit test suite" : "New test suite"}
      description="A suite executes its member test cases in order and aggregates one verdict across all of them."
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={submit} loading={pending}>
            {suite ? "Save suite" : "Create suite"}
          </Button>
        </>
      }
    >
      {error ? (
        <p className="mb-4 rounded-card bg-fog px-3 py-2 text-caption text-charcoal">
          {error}
        </p>
      ) : null}

      <div className="space-y-5">
        <FormSection title="Identity">
          <Field label="Suite name">
            <TextInput
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Customer Support Core Suite"
            />
          </Field>
          <Field
            label="Description"
            hint="What this gate protects, and who owns it."
          >
            <TextArea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
            />
          </Field>
          <Field label="Tags" hint="Comma separated. Used for filtering.">
            <TextInput
              value={tags}
              onChange={(event) => setTags(event.target.value)}
              placeholder="regression, support, release-gate"
            />
          </Field>
        </FormSection>

        <FormSection
          title="Member test cases"
          description={
            cases.data
              ? `${selected.length} of ${cases.data.total} selected`
              : "Loading test cases…"
          }
        >
          {(cases.data?.items.length ?? 0) === 0 ? (
            <p className="text-caption text-slate">
              No test cases exist yet. Create a test case first, then add it here.
            </p>
          ) : (
            <div className="ag-scroll max-h-72 space-y-2 overflow-y-auto rounded-card bg-fog/50 p-3">
              {cases.data?.items.map((item) => (
                <Checkbox
                  key={item.id}
                  label={item.name}
                  hint={`${item.agent_name || "no agent"} · ${item.scenario_tags.join(", ") || "untagged"}`}
                  checked={selected.includes(item.id)}
                  onChange={(next) =>
                    setSelected(
                      next
                        ? [...selected, item.id]
                        : selected.filter((id) => id !== item.id),
                    )
                  }
                />
              ))}
            </div>
          )}
        </FormSection>
      </div>
    </Modal>
  );
}