import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { toastError } from "@/utils/toastError";
import { listPsychTests, getTestDefinition, updateTestDefinition, importTestDefinition } from "@/services/psychTestService";
import type { PsychTest, TestDefinition } from "@/types/psychTests";
import { ClipboardList, X, Save, Loader2, Plus } from "lucide-react";

type Tab = "general" | "bedrock" | "domains" | "templates";

const AssessmentManager = () => {
  const [tests, setTests] = useState<PsychTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTest, setSelectedTest] = useState<TestDefinition | null>(null);
  const [editFields, setEditFields] = useState<Partial<TestDefinition>>({});
  const [domainEdits, setDomainEdits] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("general");
  const [loadingDef, setLoadingDef] = useState(false);
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    loadTests();
  }, []);

  const loadTests = async () => {
    try {
      setLoading(true);
      const data = await listPsychTests();
      setTests(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load tests";
      toastError(msg, 'AssessmentManager');
    } finally {
      setLoading(false);
    }
  };

  const openTest = async (testId: string) => {
    try {
      setLoadingDef(true);
      const def = await getTestDefinition(testId);
      setSelectedTest(def);
      setEditFields({});
      setDomainEdits({});
      setActiveTab("general");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load test definition";
      toastError(msg, 'AssessmentManager');
    } finally {
      setLoadingDef(false);
    }
  };

  const closePanel = () => {
    setSelectedTest(null);
    setEditFields({});
    setDomainEdits({});
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setImporting(true);
      const text = await file.text();
      const testDef = JSON.parse(text);
      const result = await importTestDefinition(testDef);
      toast.success(`Imported ${result.testId} v${result.version} (${result.questionCount} questions)`);
      loadTests();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Import failed";
      toastError(msg, 'AssessmentManager');
    } finally {
      setImporting(false);
      e.target.value = "";
    }
  };

  const updateField = <K extends keyof TestDefinition>(key: K, value: TestDefinition[K]) => {
    setEditFields((prev) => ({ ...prev, [key]: value }));
  };

  const updateDomainDesc = (key: string, value: string) => {
    setDomainEdits((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    if (!selectedTest) return;
    const updates: Partial<TestDefinition> = { ...editFields };

    // Include domain description edits if any changed
    if (Object.keys(domainEdits).length > 0) {
      updates.domainDescriptions = {
        ...(selectedTest.domainDescriptions || {}),
        ...domainEdits,
      };
    }

    if (Object.keys(updates).length === 0) {
      toast.info("No changes to save");
      return;
    }

    try {
      setSaving(true);
      const updated = await updateTestDefinition(selectedTest.testId, updates);
      setSelectedTest(updated);
      setEditFields({});
      setDomainEdits({});
      toast.success("Test definition updated");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save";
      toastError(msg, 'AssessmentManager');
    } finally {
      setSaving(false);
    }
  };

  const getVal = <K extends keyof TestDefinition>(key: K): TestDefinition[K] => {
    if (key in editFields) return editFields[key] as TestDefinition[K];
    return selectedTest![key];
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "general", label: "General" },
    { id: "bedrock", label: "Bedrock Config" },
    { id: "domains", label: "Domain Descriptions" },
    { id: "templates", label: "Interpretation Templates" },
  ];

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-legacy-purple" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-legacy-navy">Assessment Manager</h1>
        <label className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md cursor-pointer transition-colors ${
          importing ? "bg-gray-200 text-gray-500" : "bg-legacy-purple text-white hover:bg-legacy-navy"
        }`}>
          {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          {importing ? "Importing…" : "Add Assessment"}
          <input
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleImportFile}
            disabled={importing}
          />
        </label>
      </div>

      {/* Test list table */}
      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="px-4 py-3 text-left font-medium text-gray-600">Test ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Name</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Version</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Action</th>
              </tr>
            </thead>
            <tbody>
              {tests.map((t) => (
                <tr key={t.testId} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{t.testId}</td>
                  <td className="px-4 py-3">{t.testName}</td>
                  <td className="px-4 py-3">{t.version}</td>
                  <td className="px-4 py-3">
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">
                      {t.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openTest(t.testId)}
                      disabled={loadingDef}
                    >
                      Edit
                    </Button>
                  </td>
                </tr>
              ))}
              {tests.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                    <ClipboardList className="h-8 w-8 mx-auto mb-2 opacity-40" />
                    No assessments found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Edit panel */}
      {selectedTest && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-legacy-navy">
                {selectedTest.testName}
              </h2>
              <div className="flex items-center gap-2">
                <Button onClick={handleSave} disabled={saving} size="sm" className="bg-legacy-purple hover:bg-legacy-navy">
                  {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Save className="h-4 w-4 mr-1" />}
                  Save Changes
                </Button>
                <Button variant="ghost" size="sm" onClick={closePanel}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b mb-4">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? "border-legacy-purple text-legacy-purple"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* General tab */}
            {activeTab === "general" && (
              <div className="space-y-4 max-w-2xl">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Test Name</label>
                  <input
                    type="text"
                    className="w-full border rounded-md px-3 py-2 text-sm"
                    value={(getVal("testName") as string) || ""}
                    onChange={(e) => updateField("testName", e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    className="w-full border rounded-md px-3 py-2 text-sm"
                    rows={3}
                    value={(getVal("description") as string) || ""}
                    onChange={(e) => updateField("description", e.target.value)}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Estimated Minutes</label>
                    <input
                      type="number"
                      className="w-full border rounded-md px-3 py-2 text-sm"
                      value={(getVal("estimatedMinutes") as number) || 0}
                      onChange={(e) => updateField("estimatedMinutes", Number(e.target.value))}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
                    <input
                      type="text"
                      className="w-full border rounded-md px-3 py-2 text-sm bg-gray-50"
                      value={selectedTest.version}
                      disabled
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Disclaimer Text</label>
                  <textarea
                    className="w-full border rounded-md px-3 py-2 text-sm"
                    rows={3}
                    value={(getVal("disclaimerText") as string) || ""}
                    onChange={(e) => updateField("disclaimerText", e.target.value)}
                  />
                </div>
              </div>
            )}

            {/* Bedrock Config tab */}
            {activeTab === "bedrock" && (
              <div className="space-y-4 max-w-2xl">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Bedrock Prompt Template</label>
                  <p className="text-xs text-gray-500 mb-1">
                    Placeholders: {"{test_name}"}, {"{domain_scores}"}, {"{facet_scores}"}, {"{interpretation_templates}"}
                  </p>
                  <textarea
                    className="w-full border rounded-md px-3 py-2 text-sm font-mono"
                    rows={8}
                    value={(getVal("bedrockPromptTemplate") as string) || ""}
                    onChange={(e) => updateField("bedrockPromptTemplate", e.target.value)}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
                    <input
                      type="number"
                      className="w-full border rounded-md px-3 py-2 text-sm bg-gray-50"
                      value={selectedTest.bedrockConfig?.maxTokens ?? ""}
                      disabled
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
                    <input
                      type="number"
                      step="0.1"
                      className="w-full border rounded-md px-3 py-2 text-sm bg-gray-50"
                      value={selectedTest.bedrockConfig?.temperature ?? ""}
                      disabled
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cache Results (days)</label>
                    <input
                      type="number"
                      className="w-full border rounded-md px-3 py-2 text-sm bg-gray-50"
                      value={selectedTest.bedrockConfig?.cacheResultsForDays ?? ""}
                      disabled
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Model ID</label>
                    <input
                      type="text"
                      className="w-full border rounded-md px-3 py-2 text-sm bg-gray-50 text-gray-500"
                      value="anthropic.claude-3-haiku-20240307-v1:0"
                      disabled
                    />
                  </div>
                </div>
                <p className="text-xs text-gray-400">
                  Max Tokens, Temperature, Cache, and Model ID are configured in the test definition JSON. Edit the prompt template above and save.
                </p>
              </div>
            )}

            {/* Domain Descriptions tab */}
            {activeTab === "domains" && (
              <div className="space-y-4 max-w-2xl">
                {selectedTest.domainDescriptions &&
                  Object.entries(selectedTest.domainDescriptions).map(([key, value]) => (
                    <div key={key}>
                      <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">
                        {key.replace(/_/g, " ")}
                      </label>
                      <textarea
                        className="w-full border rounded-md px-3 py-2 text-sm"
                        rows={3}
                        value={domainEdits[key] ?? value}
                        onChange={(e) => updateDomainDesc(key, e.target.value)}
                      />
                    </div>
                  ))}
                {(!selectedTest.domainDescriptions ||
                  Object.keys(selectedTest.domainDescriptions).length === 0) && (
                  <p className="text-sm text-gray-400">No domain descriptions defined for this test.</p>
                )}
              </div>
            )}

            {/* Interpretation Templates tab (read-only) */}
            {activeTab === "templates" && (
              <div className="space-y-4 max-w-2xl">
                <p className="text-xs text-gray-500 mb-2">
                  Interpretation templates are read-only. Edit the test definition JSON directly to modify these.
                </p>
                {Object.entries(selectedTest.interpretationTemplates || {}).map(([key, entries]) => (
                  <div key={key} className="border rounded-md p-3">
                    <p className="text-sm font-medium text-gray-700 capitalize mb-2">
                      {key.replace(/_/g, " ")}
                    </p>
                    {entries.map((entry, idx) => (
                      <div key={idx} className="text-xs text-gray-600 mb-1">
                        <span className="font-mono text-gray-400">[{entry.min}–{entry.max}]</span>{" "}
                        {entry.text.length > 120 ? entry.text.slice(0, 120) + "…" : entry.text}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AssessmentManager;
