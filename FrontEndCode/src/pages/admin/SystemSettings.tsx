import { Card, CardContent } from "@/components/ui/card";
import { Settings, Info } from "lucide-react";

interface SettingRow {
  label: string;
  value: string;
  description: string;
}

const settings: SettingRow[] = [
  {
    label: "PSYCH_PROFILE_BEDROCK_MODEL",
    value: "anthropic.claude-3-haiku-20240307-v1:0",
    description: "AI model used for assessment narrative generation",
  },
  {
    label: "Assessment Retake Cooldown",
    value: "30 days",
    description: "Minimum days before a user can retake the same assessment",
  },
  {
    label: "Max Conversation Scoring",
    value: "—",
    description: "Placeholder for future conversation scoring limit",
  },
  {
    label: "Max Retries",
    value: "—",
    description: "Placeholder for future retry configuration",
  },
];

const SystemSettings = () => {
  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-legacy-navy">System Settings</h1>

      <div className="flex items-start gap-2 bg-blue-50 border border-blue-200 rounded-lg p-3">
        <Info className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
        <p className="text-sm text-blue-700">
          These settings are configured via SAM template environment variables.
          To change them, update <code className="bg-blue-100 px-1 rounded text-xs">template.yml</code> and redeploy.
        </p>
      </div>

      <Card>
        <CardContent className="p-0">
          {settings.map((s, idx) => (
            <div
              key={s.label}
              className={`px-4 py-4 flex items-start justify-between ${
                idx < settings.length - 1 ? "border-b" : ""
              }`}
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{s.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>
              </div>
              <span className="text-sm font-mono text-gray-700 bg-gray-100 px-2 py-1 rounded shrink-0 ml-4">
                {s.value}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="flex items-center gap-2 text-gray-400">
        <Settings className="h-4 w-4" />
        <p className="text-xs">
          Additional settings will be configurable here in future releases.
        </p>
      </div>
    </div>
  );
};

export default SystemSettings;
