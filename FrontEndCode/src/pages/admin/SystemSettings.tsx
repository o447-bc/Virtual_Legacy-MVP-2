import { useState, useEffect, useCallback, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { toast } from "@/components/ui/sonner";
import {
  Settings,
  Save,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import {
  fetchSettings,
  updateSetting,
  fetchBedrockModels,
} from "@/services/adminService";
import type { SettingItem, BedrockModel } from "@/services/adminService";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return iso;
  }
}

/** Client-side validation — returns error message or empty string. */
export function validateValue(
  valueType: SettingItem["valueType"],
  value: string
): string {
  switch (valueType) {
    case "integer": {
      const n = Number(value);
      if (value.trim() === "" || !Number.isInteger(n)) return "Must be a whole number";
      return "";
    }
    case "float": {
      if (value.trim() === "" || isNaN(Number(value))) return "Must be a valid number";
      return "";
    }
    case "string":
      if (value.trim().length === 0) return "Value cannot be empty";
      return "";
    default:
      return "";
  }
}

/** Format a model option label for the dropdown. */
export function formatModelOption(m: BedrockModel): string {
  const inPrice =
    m.inputPricePerKToken != null ? `$${m.inputPricePerKToken}/1K in` : "N/A in";
  const outPrice =
    m.outputPricePerKToken != null
      ? `$${m.outputPricePerKToken}/1K out`
      : "N/A out";
  return `${m.providerName} — ${m.modelName} (${inPrice}, ${outPrice})`;
}

/** Determine whether the save icon should be visible for a given setting. */
export function isSaveVisible(
  editedValues: Record<string, string>,
  settingKey: string,
  originalValue: string
): boolean {
  return (
    settingKey in editedValues && editedValues[settingKey] !== originalValue
  );
}

// Known Polly voices for the dropdown
const POLLY_VOICES = [
  { id: "Joanna", label: "Joanna (US English, Female)" },
  { id: "Matthew", label: "Matthew (US English, Male)" },
  { id: "Ivy", label: "Ivy (US English, Female, Child)" },
  { id: "Kendra", label: "Kendra (US English, Female)" },
  { id: "Kimberly", label: "Kimberly (US English, Female)" },
  { id: "Salli", label: "Salli (US English, Female)" },
  { id: "Joey", label: "Joey (US English, Male)" },
  { id: "Justin", label: "Justin (US English, Male, Child)" },
  { id: "Ruth", label: "Ruth (US English, Female)" },
  { id: "Stephen", label: "Stephen (US English, Male)" },
  { id: "Amy", label: "Amy (British English, Female)" },
  { id: "Brian", label: "Brian (British English, Male)" },
  { id: "Emma", label: "Emma (British English, Female)" },
  { id: "Arthur", label: "Arthur (British English, Male)" },
];

// Settings that should render as a dropdown instead of a text input
const DROPDOWN_SETTINGS: Record<string, { options: { id: string; label: string }[] }> = {
  POLLY_VOICE_ID: { options: POLLY_VOICES },
  POLLY_ENGINE: { options: [
    { id: "neural", label: "Neural (higher quality)" },
    { id: "standard", label: "Standard" },
    { id: "long-form", label: "Long-form" },
    { id: "generative", label: "Generative" },
  ]},
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const SystemSettings = () => {
  const [settings, setSettings] = useState<Record<string, SettingItem[]>>({});
  const [loading, setLoading] = useState(true);
  const [editedValues, setEditedValues] = useState<Record<string, string>>({});
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string>
  >({});
  const [savingKeys, setSavingKeys] = useState<Set<string>>(new Set());
  const [bedrockModels, setBedrockModels] = useState<BedrockModel[]>([]);
  const [openSections, setOpenSections] = useState<Set<string>>(new Set());
  const [expandedTextKeys, setExpandedTextKeys] = useState<Set<string>>(new Set());
  const fetchedRef = useRef(false);

  // ---- Data fetching ----
  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const load = async () => {
      try {
        const [settingsRes, models] = await Promise.all([
          fetchSettings(),
          fetchBedrockModels(),
        ]);
        setSettings(settingsRes.settings);
        setOpenSections(new Set()); // default collapsed
        setBedrockModels(models);
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Failed to load settings";
        toast.error(msg);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // ---- Section toggle ----
  const toggleSection = useCallback((section: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) next.delete(section);
      else next.add(section);
      return next;
    });
  }, []);

  // ---- Edit handler ----
  const handleEdit = useCallback(
    (key: string, value: string, valueType: SettingItem["valueType"]) => {
      setEditedValues((prev) => ({ ...prev, [key]: value }));
      const err = validateValue(valueType, value);
      setValidationErrors((prev) => {
        if (err) return { ...prev, [key]: err };
        const next = { ...prev };
        delete next[key];
        return next;
      });
    },
    []
  );

  // ---- Save handler ----
  const handleSave = useCallback(
    async (setting: SettingItem) => {
      const key = setting.settingKey;
      const value = editedValues[key] ?? setting.value;

      // Client-side validation
      const err = validateValue(setting.valueType, value);
      if (err) {
        setValidationErrors((prev) => ({ ...prev, [key]: err }));
        return;
      }

      setSavingKeys((prev) => new Set(prev).add(key));
      try {
        const res = await updateSetting(key, value);
        toast.success("Setting updated");

        // Update the setting in state with new metadata
        setSettings((prev) => {
          const next = { ...prev };
          for (const section of Object.keys(next)) {
            next[section] = next[section].map((s) =>
              s.settingKey === key
                ? {
                    ...s,
                    value,
                    updatedAt: res.updatedAt,
                    updatedBy: res.updatedBy,
                  }
                : s
            );
          }
          return next;
        });

        // Clear edited value
        setEditedValues((prev) => {
          const next = { ...prev };
          delete next[key];
          return next;
        });
        setValidationErrors((prev) => {
          const next = { ...prev };
          delete next[key];
          return next;
        });
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Failed to update setting";
        toast.error(msg);
      } finally {
        setSavingKeys((prev) => {
          const next = new Set(prev);
          next.delete(key);
          return next;
        });
      }
    },
    [editedValues]
  );

  // ---- Boolean toggle (auto-save) ----
  const handleBooleanToggle = useCallback(
    async (setting: SettingItem) => {
      const newValue = setting.value === "true" ? "false" : "true";
      const key = setting.settingKey;

      setSavingKeys((prev) => new Set(prev).add(key));
      try {
        const res = await updateSetting(key, newValue);
        toast.success("Setting updated");

        setSettings((prev) => {
          const next = { ...prev };
          for (const section of Object.keys(next)) {
            next[section] = next[section].map((s) =>
              s.settingKey === key
                ? {
                    ...s,
                    value: newValue,
                    updatedAt: res.updatedAt,
                    updatedBy: res.updatedBy,
                  }
                : s
            );
          }
          return next;
        });
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Failed to update setting";
        toast.error(msg);
      } finally {
        setSavingKeys((prev) => {
          const next = new Set(prev);
          next.delete(key);
          return next;
        });
      }
    },
    []
  );

  // ---- Model change handler ----
  const handleModelChange = useCallback(
    (setting: SettingItem, modelId: string) => {
      handleEdit(setting.settingKey, modelId, setting.valueType);
    },
    [handleEdit]
  );

  // ---- Render input control by valueType ----
  const renderControl = (setting: SettingItem) => {
    const key = setting.settingKey;
    const currentValue = editedValues[key] ?? setting.value;
    const hasError = !!validationErrors[key];
    const saving = savingKeys.has(key);
    const changed = isSaveVisible(editedValues, key, setting.value);

    // Check if this setting has a custom dropdown
    const dropdownConfig = DROPDOWN_SETTINGS[key];
    if (dropdownConfig && setting.valueType === "string") {
      return (
        <div className="flex items-center gap-2">
          <Select
            value={currentValue}
            onValueChange={(v) => handleEdit(key, v, setting.valueType)}
          >
            <SelectTrigger className="w-64 text-sm">
              <SelectValue placeholder="Select…" />
            </SelectTrigger>
            <SelectContent>
              {dropdownConfig.options.map((opt) => (
                <SelectItem key={opt.id} value={opt.id} className="text-sm">
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {changed && !saving && (
            <button
              onClick={() => handleSave(setting)}
              className="p-1.5 rounded-md hover:bg-gray-100 text-legacy-purple transition-colors shrink-0"
              title="Save"
            >
              <Save className="h-4 w-4" />
            </button>
          )}
          {saving && (
            <Loader2 className="h-4 w-4 animate-spin text-gray-400 shrink-0" />
          )}
        </div>
      );
    }

    switch (setting.valueType) {
      case "boolean":
        return (
          <div className="flex items-center gap-3">
            <Switch
              checked={setting.value === "true"}
              onCheckedChange={() => handleBooleanToggle(setting)}
              disabled={saving}
            />
            <span className="text-sm text-gray-600">
              {setting.value === "true" ? "Enabled" : "Disabled"}
            </span>
            {saving && (
              <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
            )}
          </div>
        );

      case "model": {
        const modelInList = bedrockModels.some(
          (m) => m.modelId === setting.value
        );
        const selectedInList = bedrockModels.some(
          (m) => m.modelId === currentValue
        );

        return (
          <div className="flex items-center gap-2 w-full">
            <div className="flex-1 min-w-0">
              {!modelInList && !changed ? (
                <div className="flex items-center gap-2 text-sm text-amber-600">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span className="truncate font-mono text-xs" title="This model may no longer be available">
                    {setting.value}
                  </span>
                </div>
              ) : (
                <Select
                  value={selectedInList ? currentValue : undefined}
                  onValueChange={(v) => handleModelChange(setting, v)}
                >
                  <SelectTrigger className="w-full text-xs">
                    <SelectValue placeholder="Select a model…" />
                  </SelectTrigger>
                  <SelectContent>
                    {bedrockModels.map((m) => (
                      <SelectItem
                        key={m.modelId}
                        value={m.modelId}
                        className="text-xs"
                      >
                        {formatModelOption(m)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
            {changed && !saving && (
              <button
                onClick={() => handleSave(setting)}
                className="p-1.5 rounded-md hover:bg-gray-100 text-legacy-purple transition-colors shrink-0"
                title="Save"
              >
                <Save className="h-4 w-4" />
              </button>
            )}
            {saving && (
              <Loader2 className="h-4 w-4 animate-spin text-gray-400 shrink-0" />
            )}
          </div>
        );
      }

      case "text":
        // Text fields use a click-to-expand pattern — rendered separately below the label row
        return null;

      case "integer":
        return (
          <div className="flex items-center gap-2">
            <Input
              type="number"
              step="1"
              value={currentValue}
              onChange={(e) =>
                handleEdit(key, e.target.value, setting.valueType)
              }
              className={`w-40 text-sm ${hasError ? "border-red-500" : ""}`}
            />
            {changed && !saving && !hasError && (
              <button
                onClick={() => handleSave(setting)}
                className="p-1.5 rounded-md hover:bg-gray-100 text-legacy-purple transition-colors shrink-0"
                title="Save"
              >
                <Save className="h-4 w-4" />
              </button>
            )}
            {saving && (
              <Loader2 className="h-4 w-4 animate-spin text-gray-400 shrink-0" />
            )}
          </div>
        );

      case "float":
        return (
          <div className="flex items-center gap-2">
            <Input
              type="number"
              step="0.01"
              value={currentValue}
              onChange={(e) =>
                handleEdit(key, e.target.value, setting.valueType)
              }
              className={`w-40 text-sm ${hasError ? "border-red-500" : ""}`}
            />
            {changed && !saving && !hasError && (
              <button
                onClick={() => handleSave(setting)}
                className="p-1.5 rounded-md hover:bg-gray-100 text-legacy-purple transition-colors shrink-0"
                title="Save"
              >
                <Save className="h-4 w-4" />
              </button>
            )}
            {saving && (
              <Loader2 className="h-4 w-4 animate-spin text-gray-400 shrink-0" />
            )}
          </div>
        );

      case "string":
      default:
        return (
          <div className="flex items-center gap-2">
            <Input
              type="text"
              value={currentValue}
              onChange={(e) =>
                handleEdit(key, e.target.value, setting.valueType)
              }
              className={`w-64 text-sm ${hasError ? "border-red-500" : ""}`}
            />
            {changed && !saving && !hasError && (
              <button
                onClick={() => handleSave(setting)}
                className="p-1.5 rounded-md hover:bg-gray-100 text-legacy-purple transition-colors shrink-0"
                title="Save"
              >
                <Save className="h-4 w-4" />
              </button>
            )}
            {saving && (
              <Loader2 className="h-4 w-4 animate-spin text-gray-400 shrink-0" />
            )}
          </div>
        );
    }
  };

  // ---- Loading state ----
  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <h1 className="text-2xl font-bold text-legacy-navy">System Settings</h1>
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <div className="animate-pulse space-y-3">
                <div className="h-5 bg-gray-200 rounded w-1/4" />
                <div className="h-4 bg-gray-100 rounded w-3/4" />
                <div className="h-10 bg-gray-100 rounded w-1/2" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const sections = Object.keys(settings);

  // ---- Main render ----
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Settings className="h-6 w-6 text-legacy-purple" />
        <h1 className="text-2xl font-bold text-legacy-navy">System Settings</h1>
      </div>

      {sections.length === 0 && (
        <Card>
          <CardContent className="p-8 text-center text-gray-400">
            <Settings className="h-8 w-8 mx-auto mb-2 opacity-40" />
            No settings found
          </CardContent>
        </Card>
      )}

      {sections.map((section) => {
        const items = settings[section];
        const isOpen = openSections.has(section);

        return (
          <Collapsible
            key={section}
            open={isOpen}
            onOpenChange={() => toggleSection(section)}
          >
            <Card>
              <CollapsibleTrigger asChild>
                <button className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition-colors rounded-t-lg">
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-semibold text-legacy-navy">
                      {section}
                    </h2>
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                      {items.length}
                    </span>
                  </div>
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-400" />
                  )}
                </button>
              </CollapsibleTrigger>

              <CollapsibleContent>
                <CardContent className="p-0">
                  {items.map((setting, idx) => {
                    const key = setting.settingKey;
                    const isTextType = setting.valueType === "text";
                    const isTextExpanded = expandedTextKeys.has(key);
                    const textCurrentValue = editedValues[key] ?? setting.value;
                    const textChanged = isSaveVisible(editedValues, key, setting.value);
                    const textSaving = savingKeys.has(key);

                    return (
                    <div
                      key={setting.settingKey}
                      className={`px-6 py-4 ${
                        idx < items.length - 1 ? "border-b" : ""
                      }`}
                    >
                      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                        {/* Label + description */}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900">
                            {setting.label}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {setting.description}
                          </p>
                        </div>

                        {/* Input control (non-text types) */}
                        {!isTextType && (
                          <div className="shrink-0">{renderControl(setting)}</div>
                        )}

                        {/* Text type: show preview / expand button */}
                        {isTextType && !isTextExpanded && (
                          <button
                            onClick={() => setExpandedTextKeys((prev) => new Set(prev).add(key))}
                            className="text-left shrink-0 max-w-xs lg:max-w-sm"
                          >
                            <span className="text-xs font-mono text-gray-500 bg-gray-50 border border-gray-200 rounded px-3 py-1.5 block truncate hover:bg-gray-100 transition-colors cursor-pointer">
                              {setting.value ? (setting.value.length > 60 ? setting.value.slice(0, 60) + "…" : setting.value) : "Click to edit…"}
                            </span>
                          </button>
                        )}
                      </div>

                      {/* Text type: expanded full-width textarea */}
                      {isTextType && isTextExpanded && (
                        <div className="mt-3">
                          <Textarea
                            rows={8}
                            value={textCurrentValue}
                            onChange={(e) =>
                              handleEdit(key, e.target.value, setting.valueType)
                            }
                            className="w-full text-sm font-mono"
                            autoFocus
                          />
                          <div className="flex items-center gap-2 mt-2">
                            {textChanged && !textSaving && (
                              <button
                                onClick={() => handleSave(setting)}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-legacy-purple text-white text-xs hover:bg-legacy-navy transition-colors"
                              >
                                <Save className="h-3.5 w-3.5" />
                                Save
                              </button>
                            )}
                            {textSaving && (
                              <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                            )}
                            <button
                              onClick={() => {
                                setExpandedTextKeys((prev) => {
                                  const next = new Set(prev);
                                  next.delete(key);
                                  return next;
                                });
                                // Discard unsaved edits
                                setEditedValues((prev) => {
                                  const next = { ...prev };
                                  delete next[key];
                                  return next;
                                });
                              }}
                              className="px-3 py-1.5 rounded-md text-xs text-gray-500 hover:bg-gray-100 transition-colors"
                            >
                              Collapse
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Validation error */}
                      {validationErrors[setting.settingKey] && (
                        <p className="text-xs text-red-500 mt-1">
                          {validationErrors[setting.settingKey]}
                        </p>
                      )}

                      {/* Metadata */}
                      <p className="text-xs text-gray-400 mt-2">
                        Last updated by {setting.updatedBy} at{" "}
                        {formatDate(setting.updatedAt)}
                      </p>
                    </div>
                    );
                  })}
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        );
      })}
    </div>
  );
};

export default SystemSettings;
