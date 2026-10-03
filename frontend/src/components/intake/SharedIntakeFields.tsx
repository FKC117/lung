import type { ReactNode } from "react";
import type { EntryOption } from "../../api";

interface FieldShellProps {
  populated?: boolean;
  label: string;
  required?: boolean;
  fullWidth?: boolean;
  className?: string;
  help?: string;
  children: ReactNode;
  action?: ReactNode;
  kind: "text-field" | "select-field" | "textarea-field";
}

function FieldShell({ label, required, fullWidth, className = "", help, children, kind, action, populated }: FieldShellProps) {
  const field = <label className={`${fullWidth ? "filter-field entry-span-full" : "filter-field"} ${className}`.trim()} data-field-populated={populated || undefined} data-intake-component={kind} data-intake-label={label}>
    <span>{label}{required ? " *" : ""}</span>
    {children}
    {help ? <p className="entry-field-help">{help}</p> : null}
  </label>;
  return action ? <div className={fullWidth ? "filter-field entry-span-full" : "filter-field"}>{field}{action}</div> : field;
}

export interface IntakeTextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  readOnly?: boolean;
  disabled?: boolean;
  help?: string;
  control?: ReactNode;
  fullWidth?: boolean;
  evidence?: ReactNode;
}

export function IntakeTextField({ label, value, onChange, type = "text", required, readOnly, disabled, help, control, fullWidth, evidence }: IntakeTextFieldProps) {
  return <FieldShell label={label} required={required} help={help} fullWidth={fullWidth} populated={value.trim().length > 0} kind="text-field">
    {evidence}
    {control ?? <input className="auth-input" type={type} required={required} readOnly={readOnly} disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} />}
  </FieldShell>;
}

export interface IntakeSelectFieldProps {
  action?: ReactNode;
  label: string;
  value: string | number;
  options: EntryOption[];
  onChange: (value: string, option?: EntryOption) => void;
  required?: boolean;
  disabled?: boolean;
  help?: string;
  placeholder?: string;
  optionLabel?: (option: EntryOption) => string;
  evidence?: ReactNode;
}

export function IntakeSelectField({ label, value, options, onChange, required, disabled, help, evidence, action, placeholder = "Select…", optionLabel = (option) => option.name ?? option.display }: IntakeSelectFieldProps) {
  return <FieldShell label={label} required={required} help={help} action={action} populated={String(value).trim().length > 0} kind="select-field">
    {evidence}
    <select className="filter-select" value={value} required={required} disabled={disabled} onChange={(event) => onChange(event.target.value, options.find((option) => String(option.id) === event.target.value))}>
      <option value="">{placeholder}</option>
      {options.map((option) => <option key={option.id} value={option.id}>{optionLabel(option)}</option>)}
    </select>
  </FieldShell>;
}

export interface IntakeTextAreaProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  fullWidth?: boolean;
  className?: string;
  help?: string;
  evidence?: ReactNode;
}

export function IntakeTextArea({ label, value, onChange, disabled, fullWidth = true, className, help, evidence }: IntakeTextAreaProps) {
  return <FieldShell label={label} fullWidth={fullWidth} className={className} help={help} populated={value.trim().length > 0} kind="textarea-field">
    {evidence}
    <textarea className="auth-input entry-textarea" disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} />
  </FieldShell>;
}
