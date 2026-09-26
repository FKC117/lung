// @vitest-environment jsdom
import { useState } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { EntriesPatientMatch, LongitudinalIntakeDraft, PrescriptionObservationDraft } from "../../api";
import { emptyObservation, observationCollections } from "./draftWorkspace";
import { createBlankRecord, observationFieldSchemas } from "./observationFieldSchema";
import { ObservationFormSections } from "./ObservationFormSections";
import { PatientFormSections } from "./PatientFormSections";
import manualEntrySource from "../../pages/EntriesPatientEntryPage.tsx?raw";

afterEach(cleanup);

const blankPatient: LongitudinalIntakeDraft["patient"] = { match_status: "unresolved", patient_id: null, values: {} };

describe("shared intake form fields", () => {
  it("uses the same field primitive in manual and prescription entry", () => {
    expect(manualEntrySource).toContain("return <IntakeTextField");
    expect(manualEntrySource).toContain("return <IntakeSelectField");
    expect(manualEntrySource).toContain("return <IntakeTextArea");
    render(<PatientFormSections patient={blankPatient} onChange={() => undefined} />);
    expect(document.querySelector('[data-intake-component="text-field"]')).not.toBeNull();
  });

  it("initializes every blank collection record with its complete explicit schema", () => {
    for (const collection of observationCollections) {
      expect(Object.keys(createBlankRecord(collection).values)).toEqual(observationFieldSchemas[collection].fields.map((field) => field.key));
    }
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
