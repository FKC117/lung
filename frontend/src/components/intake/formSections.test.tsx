// @vitest-environment jsdom
import { useState } from "react";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { EntriesPatientMatch, LongitudinalIntakeDraft, PrescriptionObservationDraft } from "../../api";
import { emptyObservation, observationCollections } from "./draftWorkspace";
import { anthropometrySectionSchema, createBlankRecord, observationFieldSchemas } from "./observationFieldSchema";
import { ObservationFormSections } from "./ObservationFormSections";
import { PatientFormSections } from "./PatientFormSections";
import { ClinicalSectionFields } from "./ClinicalSectionFields";

afterEach(cleanup);

const blankPatient: LongitudinalIntakeDraft["patient"] = { match_status: "unresolved", patient_id: null, values: {} };

describe("shared intake form fields", () => {
  it("renders manual and prescription fields from the same authoritative definitions", () => {
    render(<><ClinicalSectionFields fields={observationFieldSchemas.histopathologies.fields} values={{}} binding="manual" onChange={() => undefined} /><ClinicalSectionFields fields={observationFieldSchemas.histopathologies.fields} values={{}} binding="canonical" onChange={() => undefined} /></>);
    const manual = document.querySelector('[data-clinical-schema-binding="manual"]');
    const canonical = document.querySelector('[data-clinical-schema-binding="canonical"]');
    expect(manual).not.toBeNull(); expect(canonical).not.toBeNull();
    for (const field of observationFieldSchemas.histopathologies.fields) {
      expect(within(manual as HTMLElement).getByText((content) => content.startsWith(field.label))).toBeTruthy();
      expect(within(canonical as HTMLElement).getByText((content) => content.startsWith(field.label))).toBeTruthy();
    }
  });

  it("initializes every blank collection record with its complete explicit schema", () => {
    for (const collection of observationCollections) {
      expect(Object.keys(createBlankRecord(collection).values)).toEqual(observationFieldSchemas[collection].fields.filter((field) => !field.readOnly).map((field) => field.key));
    }
  });

  it("matches normalized anthropometry, marker, pathology, treatment, radiotherapy, and outcome names", () => {
    const keys = (section: keyof typeof observationFieldSchemas) => observationFieldSchemas[section].fields.map((field) => field.key);
    expect(anthropometrySectionSchema.fields.map((field) => field.key)).toEqual(["height_cm", "weight_kg", "bmi", "bsa"]);
    expect(keys("cancer_markers")).toEqual(["marker", "value", "unit", "tested_on", "notes"]);
    expect(observationFieldSchemas.diagnoses.fields.find((field) => field.key === "metastatic_sites")?.resource).toBe("diagnosis-metastatic-sites");
    expect(keys("histopathologies")).toEqual(expect.arrayContaining(["report_date", "report_summary", "any_known_mutation"]));
    expect(keys("molecular_tests")).toEqual(expect.arrayContaining(["tested_on", "reported_on", "panel_target", "alteration_type", "variant_allele_frequency"]));
    expect(keys("treatments")).toEqual(expect.arrayContaining(["started_on", "ended_on", "administered_on", "cycle_number", "dose_unit"]));
    expect(keys("surgeries")).toEqual(expect.arrayContaining(["modality", "laterality", "surgery_date"]));
    expect(keys("radiotherapies")).toEqual(expect.arrayContaining(["dose_per_fraction_cgy", "planned_fractions", "planned_total_dose_cgy", "delivered_total_dose_cgy"]));
    expect(keys("recist_assessments")).toEqual(expect.arrayContaining(["assessed_on", "timepoint", "overall_response"]));
    expect(keys("pathological_responses")).toContain("residual_viable_tumor_percentage");
  });

  it("derives anthropometry calculations and cancer-marker unit without editable unit state", () => {
    const { unmount } = render(<ClinicalSectionFields fields={anthropometrySectionSchema.fields} values={{ height_cm: "170", weight_kg: "70" }} binding="manual" onChange={() => undefined} />);
    expect(screen.getByDisplayValue("24.22")).toHaveProperty("readOnly", true);
    expect(screen.getByDisplayValue("1.82")).toHaveProperty("readOnly", true);
    unmount();
    render(<ClinicalSectionFields fields={observationFieldSchemas.cancer_markers.fields} values={{ marker_name: "7" }} catalog={{ "cancer-marker-names": [{ id: 7, name: "CEA", display: "CEA", unit: "ng/mL" }] }} binding="manual" onChange={() => undefined} />);
    expect(screen.getByDisplayValue("ng/mL")).toHaveProperty("readOnly", true);
  });

  it("stores multi-select values as option IDs and plural resolutions", async () => {
    function Harness() {
      const [observation, setObservation] = useState<PrescriptionObservationDraft>({ ...emptyObservation(), diagnoses: [createBlankRecord("diagnoses")] });
      const record = observation.diagnoses[0];
      return <><ObservationFormSections observation={observation} catalog={{ "diagnosis-metastatic-sites": [{ id: 11, name: "Liver", display: "Liver" }, { id: 12, name: "Bone", display: "Bone" }] }} onChange={setObservation} /><output data-testid="multi-values">{JSON.stringify(record.values.metastatic_sites)}</output><output data-testid="multi-resolution">{JSON.stringify(record.resolutions.metastatic_sites?.option_ids)}</output></>;
    }
    render(<Harness />);
    await userEvent.selectOptions(screen.getByRole("listbox", { name: /Metastatic sites/ }), ["11", "12"]);
    expect(screen.getByTestId("multi-values").textContent).toBe("[11,12]");
    expect(screen.getByTestId("multi-resolution").textContent).toBe("[11,12]");
  });

  it("renders all fields when a blank diagnosis is added", async () => {
    function Harness() {
      const [observation, setObservation] = useState<PrescriptionObservationDraft>(emptyObservation());
      return <ObservationFormSections observation={observation} onChange={setObservation} />;
    }
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Add Diagnosis" }));
    for (const field of observationFieldSchemas.diagnoses.fields) expect(screen.getByText((content) => content.startsWith(field.label))).toBeTruthy();
  });
});

describe("existing patient matching", () => {
  it("searches registry patients and applies the selected match", async () => {
    const match: EntriesPatientMatch = { id: 42, patient_id: "REG-0042", name: "Matched Patient", phone: "01700000000", registration_no: "H-42" };
    const searchPatients = vi.fn(async () => ({ results: [match] }));
    function Harness() {
      const [patient, setPatient] = useState<LongitudinalIntakeDraft["patient"]>({ ...blankPatient, match_status: "existing" });
      return <><PatientFormSections patient={patient} onChange={setPatient} searchPatients={searchPatients} /><output data-testid="patient-id">{patient.patient_id}</output></>;
    }
    render(<Harness />);
    await userEvent.type(screen.getByRole("textbox", { name: /Find existing patient/ }), "REG-0042");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(searchPatients).toHaveBeenCalledWith("REG-0042"));
    await userEvent.click(await screen.findByRole("button", { name: /Matched Patient/ }));
    expect(screen.getByTestId("patient-id").textContent).toBe("42");
    expect(screen.queryByLabelText("Matched database patient ID")).toBeNull();
  });
});
