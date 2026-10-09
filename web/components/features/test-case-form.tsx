"use client";

import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import {
  Checkbox,
  Field,
  FormGrid,
  FormSection,
  SelectInput,
  TextArea,
  TextInput,
} from "@/components/fields";
import { Modal } from "@/components/modal";
import { Badge, Button, IconButton } from "@/components/ui";
import { endpoints } from "@/lib/api/endpoints";
import type {
  Constraint,
  ConstraintType,
  Dimension,
  TestCase,
  TestCaseCreateInput,
} from "@/lib/api/types";
import {
  DIMENSION_LABEL,
  DIMENSION_ORDER,
  SEVERITY_LABEL,
  SEVERITY_ORDER,
  parseListInput,
  parseNumberListInput,
} from "@/lib/format";
import { toApiError } from "@/lib/hooks";

const CONSTRAINT_TYPES: ConstraintType[] = [
  "max_words",
  "min_words",
  "must_include",
  "must_exclude",
  "must_answer_prompt",
  "ascii_letters_only",
  "non_empty",
  "no_all_caps_shouting",
];

const NEEDS_VALUE: ConstraintType[] = ["max_words", "min_words"];
const NEEDS_PHRASES: ConstraintType[] = ["must_include", "must_exclude"];

interface FormState {
  name: string;
  description: string;
  agent_name: string;
  scenario_tags: string;
  input_prompt: string;
  expected_answer: string;
  referenced_facts: string;
  required_keywords: string;
  forbidden_keywords: string;
  expected_numbers: string;
  require_disclaimer: boolean;
  constraints: Constraint[];
  thresholds: Record<string, number>;
  weights: Record<string, number>;
  enabled_dimensions: Dimension[];
  sample_good_response: string;
}

const EMPTY: FormState = {
  name: "",
  description: "",
  agent_name: "",
  scenario_tags: "",
  input_prompt: "",
  expected_answer: "",
  referenced_facts: "",
  required_keywords: "",
  forbidden_keywords: "",
  expected_numbers: "",
  require_disclaimer: true,
  constraints: [],
  thresholds: {},
  weights: {},
  enabled_dimensions: [...DIMENSION_ORDER],
  sample_good_response: "",
};

function toForm(testCase: TestCase): FormState {
  return {
    name: testCase.name,
    description: testCase.description,
    agent_name: testCase.agent_name,
    scenario_tags: testCase.scenario_tags.join(", "),
    input_prompt: testCase.input_prompt,
    expected_answer: testCase.expected_answer,
    referenced_facts: testCase.referenced_facts.join(", "),
    required_keywords: testCase.required_keywords.join(", "),
    forbidden_keywords: testCase.forbidden_keywords.join(", "),
    expected_numbers: testCase.expected_numbers.join(", "),
    require_disclaimer: testCase.require_disclaimer,
    constraints: testCase.constraints ?? [],
    thresholds: testCase.thresholds ?? {},
    weights: testCase.weights ?? {},
    enabled_dimensions: testCase.enabled_dimensions ?? [...DIMENSION_ORDER],
    sample_good_response: testCase.sample_good_response ?? "",
  };
}

function toPayload(form: FormState): TestCaseCreateInput {
  return {
    name: form.name.trim(),
    description: form.description,
    agent_name: form.agent_name.trim(),
    scenario_tags: parseListInput(form.scenario_tags),
    input_prompt: form.input_prompt,
    expected_answer: form.expected_answer,
    referenced_facts: parseListInput(form.referenced_facts),
    required_keywords: parseListInput(form.required_keywords),
    forbidden_keywords: parseListInput(form.forbidden_keywords),
    expected_numbers: parseNumberListInput(form.expected_numbers),
    require_disclaimer: form.require_disclaimer,
    constraints: form.constraints,
    thresholds: form.thresholds,
    weights: form.weights,
    enabled_dimensions: form.enabled_dimensions,
    sample_good_response: form.sample_good_response || null,
  };
}

export function TestCaseForm({
  open,
  testCase,
  onClose,
  onSaved,
}: {
  open: boolean;
  testCase: TestCase | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(testCase ? toForm(testCase) : EMPTY);
    setError(null);
  }, [open, testCase]);

  function patch(next: Partial<FormState>) {
    setForm((current) => ({ ...current, ...next }));
  }

  function toggleDimension(dimension: Dimension, enabled: boolean) {
    patch({
      enabled_dimensions: enabled
        ? [...form.enabled_dimensions, dimension]
        : form.enabled_dimensions.filter((entry) => entry !== dimension),
    });
  }

  async function submit() {
    setError(null);
    if (form.name.trim().length < 3) {
      setError("Name must be at least 3 characters.");
      return;
    }
    if (!form.input_prompt.trim()) {
      setError("Input prompt is required.");
      return;
    }
    if (!form.expected_answer.trim()) {
      setError("Expected answer is required — it is the grounding source.");
      return;
    }
    if (form.enabled_dimensions.length === 0) {
      setError("Enable at least one dimension.");
      return;
    }
    const invalid = form.constraints.find(
      (constraint) =>
        NEEDS_VALUE.includes(constraint.type) &&
        (constraint.value === null ||
          constraint.value === undefined ||
          constraint.value === ""),
    );
    if (invalid) {
      setError(`Constraint “${invalid.type}” requires a numeric value.`);
      return;
    }

    setPending(true);
    try {
      const payload = toPayload(form);
      if (testCase) {
        await endpoints.updateTestCase(testCase.id, payload);
      } else {
        await endpoints.createTestCase(payload);
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
      title={testCase ? "Edit test case" : "New test case"}
      description="The expected answer plus referenced facts form the grounding source every hallucination check measures against."
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={submit} loading={pending}>
            {testCase ? "Save changes" : "Create test case"}
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
          <FormGrid>
            <Field label="Name" hint="Unique across the workspace.">
              <TextInput
                value={form.name}
                onChange={(event) => patch({ name: event.target.value })}
                placeholder="Refund eligibility outside the window"
              />
            </Field>
            <Field label="Agent name" hint="Which agent this case targets.">
              <TextInput
                value={form.agent_name}
                onChange={(event) => patch({ agent_name: event.target.value })}
                placeholder="support-agent-v2"
              />
            </Field>
          </FormGrid>
          <Field label="Description">
            <TextArea
              rows={2}
              value={form.description}
              onChange={(event) => patch({ description: event.target.value })}
            />
          </Field>
          <Field label="Scenario tags" hint="Comma separated.">
            <TextInput
              value={form.scenario_tags}
              onChange={(event) => patch({ scenario_tags: event.target.value })}
              placeholder="refunds, policy, billing"
            />
          </Field>
        </FormSection>

        <FormSection
          title="Grounding source"
          description="The expected answer plus referenced facts are what hallucination checks measure claims against."
        >
          <Field label="Input prompt">
            <TextArea
              rows={3}
              value={form.input_prompt}
              onChange={(event) => patch({ input_prompt: event.target.value })}
              placeholder="Customer asks whether their 45-day-old order can still be refunded."
            />
          </Field>
          <Field label="Expected answer">
            <TextArea
              rows={3}
              value={form.expected_answer}
              onChange={(event) => patch({ expected_answer: event.target.value })}
              placeholder="Refunds are available within 30 days of purchase."
            />
          </Field>
          <Field
            label="Referenced facts"
            hint="Comma separated. Any claim contradicting one of these is marked verified."
          >
            <TextArea
              rows={2}
              value={form.referenced_facts}
              onChange={(event) => patch({ referenced_facts: event.target.value })}
              placeholder="refund window is 30 days"
            />
          </Field>
        </FormSection>

        <FormSection
          title="Scoring signals"
          description="These feed the accuracy dimension directly."
        >
          <FormGrid>
            <Field label="Required keywords" hint="Comma separated.">
              <TextInput
                value={form.required_keywords}
                onChange={(event) =>
                  patch({ required_keywords: event.target.value })
                }
                placeholder="30 days, refund"
              />
            </Field>
            <Field label="Forbidden keywords" hint="Presence caps accuracy at 40.">
              <TextInput
                value={form.forbidden_keywords}
                onChange={(event) =>
                  patch({ forbidden_keywords: event.target.value })
                }
                placeholder="guaranteed, always approved"
              />
            </Field>
            <Field label="Expected numbers" hint="Comma separated.">
              <TextInput
                value={form.expected_numbers}
                onChange={(event) =>
                  patch({ expected_numbers: event.target.value })
                }
                placeholder="30"
              />
            </Field>
          </FormGrid>
          <Checkbox
            label="Require a disclaimer"
            hint="When enabled, safety runs the disclaimer rules; otherwise they are reported as skipped."
            checked={form.require_disclaimer}
            onChange={(next) => patch({ require_disclaimer: next })}
          />
        </FormSection>

        <FormSection
          title="Enabled dimensions"
          description="Disabled dimensions are excluded and the remaining weights are renormalised by the engine."
        >
          <div className="grid gap-2 sm:grid-cols-2">
            {DIMENSION_ORDER.map((dimension) => (
              <Checkbox
                key={dimension}
                label={DIMENSION_LABEL[dimension]}
                checked={form.enabled_dimensions.includes(dimension)}
                onChange={(next) => toggleDimension(dimension, next)}
              />
            ))}
          </div>
        </FormSection>

        <FormSection
          title="Thresholds and weights"
          description="Leave blank to use the engine default for that dimension. Weights are renormalised across enabled dimensions."
        >
          <div className="space-y-3">
            {DIMENSION_ORDER.map((dimension) => (
              <div
                key={dimension}
                className="grid grid-cols-[minmax(0,1fr)_5.5rem_5.5rem] items-center gap-3"
              >
                <span className="truncate text-caption text-charcoal">
                  {DIMENSION_LABEL[dimension]}
                </span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  aria-label={`${DIMENSION_LABEL[dimension]} threshold`}
                  placeholder="threshold"
                  value={form.thresholds[dimension] ?? ""}
                  onChange={(event) => {
                    const raw = event.target.value;
                    const next = { ...form.thresholds };
                    if (raw === "") delete next[dimension];
                    else next[dimension] = Number(raw);
                    patch({ thresholds: next });
                  }}
                  className="ag-num h-10 w-full rounded-card bg-paper px-2.5 text-caption text-charcoal shadow-hairline outline-none transition-shadow duration-150 ease-out placeholder:text-pebble focus:shadow-hairline-strong"
                />
                <input
                  type="number"
                  min={0}
                  step={0.05}
                  aria-label={`${DIMENSION_LABEL[dimension]} weight`}
                  placeholder="weight"
                  value={form.weights[dimension] ?? ""}
                  onChange={(event) => {
                    const raw = event.target.value;
                    const next = { ...form.weights };
                    if (raw === "") delete next[dimension];
                    else next[dimension] = Number(raw);
                    patch({ weights: next });
                  }}
                  className="ag-num h-10 w-full rounded-card bg-paper px-2.5 text-caption text-charcoal shadow-hairline outline-none transition-shadow duration-150 ease-out placeholder:text-pebble focus:shadow-hairline-strong"
                />
              </div>
            ))}
          </div>
        </FormSection>

        <FormSection
          title="Sample good response"
          description="Used by the demo seeder and by the suite executor. It must pass the enabled dimensions."
        >
          <TextArea
            rows={3}
            value={form.sample_good_response}
            onChange={(event) =>
              patch({ sample_good_response: event.target.value })
            }
            placeholder="Refunds are available within 30 days of purchase. Your order is outside that window."
          />
        </FormSection>

        <FormSection
          title="Instruction constraints"
          description="Each type maps to an independent validator in the compliance module. Score = 100 − 100 × (violations ÷ constraints)."
        >
          {form.constraints.length === 0 ? (
            <p className="text-caption text-slate">
              No constraints declared. The compliance dimension scores 100 when the
              list is empty.
            </p>
          ) : (
            <div className="space-y-3">
              {form.constraints.map((constraint, index) => (
                <div
                  key={index}
                  className="grid items-end gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_8rem_auto]"
                >
                  <Field label="Type">
                    <SelectInput
                      value={constraint.type}
                      onChange={(event) => {
                        const next = [...form.constraints];
                        next[index] = {
                          ...constraint,
                          type: event.target.value as ConstraintType,
                        };
                        patch({ constraints: next });
                      }}
                    >
                      {CONSTRAINT_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {type.replace(/_/g, " ")}
                        </option>
                      ))}
                    </SelectInput>
                  </Field>

                  <Field label="Value or phrases">
                    {NEEDS_VALUE.includes(constraint.type) ? (
                      <TextInput
                        type="number"
                        value={
                          constraint.value === null ||
                          constraint.value === undefined
                            ? ""
                            : String(constraint.value)
                        }
                        onChange={(event) => {
                          const next = [...form.constraints];
                          next[index] = {
                            ...constraint,
                            value:
                              event.target.value === ""
                                ? null
                                : Number(event.target.value),
                          };
                          patch({ constraints: next });
                        }}
                      />
                    ) : NEEDS_PHRASES.includes(constraint.type) ? (
                      <TextInput
                        value={(constraint.phrases ?? []).join(", ")}
                        placeholder="must contain this phrase"
                        onChange={(event) => {
                          const next = [...form.constraints];
                          next[index] = {
                            ...constraint,
                            phrases: parseListInput(event.target.value),
                          };
                          patch({ constraints: next });
                        }}
                      />
                    ) : (
                      <TextInput
                        disabled
                        value=""
                        placeholder="no value required"
                      />
                    )}
                  </Field>

                  <Field label="Severity">
                    <SelectInput
                      value={constraint.severity ?? "medium"}
                      onChange={(event) => {
                        const next = [...form.constraints];
                        next[index] = {
                          ...constraint,
                          severity: event.target.value as never,
                        };
                        patch({ constraints: next });
                      }}
                    >
                      {SEVERITY_ORDER.map((severity) => (
                        <option key={severity} value={severity}>
                          {SEVERITY_LABEL[severity]}
                        </option>
                      ))}
                    </SelectInput>
                  </Field>

                  <IconButton
                    label="Remove constraint"
                    tone="danger"
                    className="mb-1"
                    onClick={() =>
                      patch({
                        constraints: form.constraints.filter(
                          (_, position) => position !== index,
                        ),
                      })
                    }
                  >
                    <Trash2 size={15} />
                  </IconButton>
                </div>
              ))}
            </div>
          )}

          <Button
            variant="ghost"
            size="sm"
            icon={<Plus size={14} />}
            onClick={() =>
              patch({
                constraints: [
                  ...form.constraints,
                  { type: "max_words", value: 120, severity: "medium" },
                ],
              })
            }
          >
            Add constraint
          </Button>
        </FormSection>
      </div>
    </Modal>
  );
}