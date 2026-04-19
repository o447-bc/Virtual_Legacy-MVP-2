import React, { useState, useEffect } from "react";
import { fetchAuthSession } from "aws-amplify/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  ADMIN_EMAIL_CAPTURE_METRICS_URL,
  ADMIN_EMAIL_CAPTURE_EMAILS_URL,
  ADMIN_EMAIL_CAPTURE_CONFIG_URL,
  ADMIN_EMAIL_CAPTURE_AB_RESULTS_URL,
  ADMIN_EMAIL_CAPTURE_TEST_SEND_URL,
} from "@/config/api";
import {
  Mail,
  TrendingUp,
  Users,
  Clock,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Send,
  Pause,
  Play,
} from "lucide-react";

// ── helpers ──────────────────────────────────────────────────────────────────

async function getAuthHeaders(): Promise<Record<string, string>> {
  const session = await fetchAuthSession();
  const idToken = session.tokens?.idToken?.toString();
  if (!idToken) throw new Error("No authentication token available");
  return { Authorization: `Bearer ${idToken}`, "Content-Type": "application/json" };
}

function pct(n: number, total: number): string {
  if (!total) return "0%";
  return `${((n / total) * 100).toFixed(1)}%`;
}

function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString();
}

const STAGE_LABELS: Record<number, string> = {
  0: "Welcome",
  1: "7-day",
  2: "14-day",
  3: "28-day",
  4: "56-day (final)",
  5: "Win-back",
};

// ── component ────────────────────────────────────────────────────────────────

const AdminEmailCapture: React.FC = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [emails, setEmails] = useState<any[]>([]);
  const [abResults, setAbResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // config state
  const [configIntervals, setConfigIntervals] = useState<Record<string, number>>({
    stage1: 7, stage2: 14, stage3: 28, stage4: 56,
  });
  const [paused, setPaused] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [sendingTest, setSendingTest] = useState<string | null>(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const headers = await getAuthHeaders();

      const [metricsRes, emailsRes, abRes] = await Promise.all([
        fetch(ADMIN_EMAIL_CAPTURE_METRICS_URL, { headers }),
        fetch(ADMIN_EMAIL_CAPTURE_EMAILS_URL, { headers }),
        fetch(ADMIN_EMAIL_CAPTURE_AB_RESULTS_URL, { headers }),
      ]);

      if (metricsRes.ok) {
        const m = await metricsRes.json();
        setMetrics(m);
        // seed config from metrics if present
        if (m.schedule) setConfigIntervals(m.schedule);
        if (typeof m.paused === "boolean") setPaused(m.paused);
      }
      if (emailsRes.ok) {
        const data = await emailsRes.json();
        setEmails(data.items || []);
      }
      if (abRes.ok) setAbResults(await abRes.json());
    } catch (e) {
      console.error("Failed to load email capture data", e);
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      setSavingConfig(true);
      const headers = await getAuthHeaders();
      await fetch(ADMIN_EMAIL_CAPTURE_CONFIG_URL, {
        method: "PUT",
        headers,
        body: JSON.stringify({ schedule: configIntervals, paused }),
      });
    } catch (e) {
      console.error("Failed to save config", e);
    } finally {
      setSavingConfig(false);
    }
  };

  const sendTestReminder = async (email: string) => {
    try {
      setSendingTest(email);
      const headers = await getAuthHeaders();
      await fetch(ADMIN_EMAIL_CAPTURE_TEST_SEND_URL, {
        method: "POST",
        headers,
        body: JSON.stringify({ email }),
      });
    } catch (e) {
      console.error("Failed to send test reminder", e);
    } finally {
      setSendingTest(null);
    }
  };

  // ── loading / error states ──

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-legacy-purple" />
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="p-6">
        <p className="text-red-500">Failed to load email capture data.</p>
        <Button onClick={loadData} className="mt-2">Retry</Button>
      </div>
    );
  }

  // ── derived values ──

  const total = metrics.total || 0;
  const converted = metrics.converted || 0;
  const expired = metrics.expired || 0;
  const unsubscribed = metrics.unsubscribed || 0;
  const bounced = metrics.bounced || 0;
  const active = metrics.active || 0;
  const conversionRate = total ? ((converted / total) * 100).toFixed(1) : "0";
  const bounceRate = total ? ((bounced / total) * 100).toFixed(1) : "0";

  const funnelStages = metrics.funnelStages || {};
  const conversionByStage = metrics.conversionByStage || {};
  const conversionBySource = metrics.conversionBySource || {};
  const timeToConvert = metrics.timeToConvert || {};
  const referrals = metrics.referrals || {};

  // filter emails
  const filteredEmails = statusFilter === "all"
    ? emails
    : emails.filter((e: any) => {
        if (statusFilter === "converted") return !!e.convertedAt;
        if (statusFilter === "expired") return !!e.expiredAt;
        if (statusFilter === "unsubscribed") return !!e.unsubscribedAt;
        if (statusFilter === "bounced") return e.bounceStatus === "hard";
        if (statusFilter === "active") return !e.convertedAt && !e.expiredAt && !e.unsubscribedAt && e.bounceStatus !== "hard";
        return true;
      });

  // ── render ──

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-legacy-navy">Email Capture &amp; Nurture</h1>
        <Button variant="outline" size="sm" onClick={loadData}>
          <RefreshCw className="h-4 w-4 mr-1" /> Refresh
        </Button>
      </div>

      {/* ── Metrics Cards ── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card>
          <CardContent className="p-4 text-center">
            <Mail className="h-5 w-5 mx-auto mb-1 text-legacy-purple" />
            <p className="text-2xl font-bold">{total}</p>
            <p className="text-xs text-gray-500">Total Captured</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <TrendingUp className="h-5 w-5 mx-auto mb-1 text-green-600" />
            <p className="text-2xl font-bold">{conversionRate}%</p>
            <p className="text-xs text-gray-500">Conversion Rate</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Users className="h-5 w-5 mx-auto mb-1 text-blue-600" />
            <p className="text-2xl font-bold">{active}</p>
            <p className="text-xs text-gray-500">Active Nurture</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Clock className="h-5 w-5 mx-auto mb-1 text-amber-500" />
            <p className="text-2xl font-bold">{expired}</p>
            <p className="text-xs text-gray-500">Expired</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <XCircle className="h-5 w-5 mx-auto mb-1 text-red-500" />
            <p className="text-2xl font-bold">{unsubscribed}</p>
            <p className="text-xs text-gray-500">Unsubscribed</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <AlertTriangle className="h-5 w-5 mx-auto mb-1 text-orange-500" />
            <p className="text-2xl font-bold">{bounceRate}%</p>
            <p className="text-xs text-gray-500">Bounce Rate</p>
          </CardContent>
        </Card>
      </div>

      {/* ── Funnel Status ── */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Funnel Status</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 text-center text-sm">
            {[0, 1, 2, 3, 4].map((stage) => (
              <div key={stage} className="bg-gray-50 rounded p-3">
                <p className="font-semibold text-lg">{funnelStages[stage] ?? 0}</p>
                <p className="text-xs text-gray-500">Stage {stage}</p>
                <p className="text-xs text-gray-400">{STAGE_LABELS[stage]}</p>
                <p className="text-xs text-gray-400">{pct(funnelStages[stage] ?? 0, total)}</p>
              </div>
            ))}
            <div className="bg-green-50 rounded p-3">
              <p className="font-semibold text-lg text-green-700">{converted}</p>
              <p className="text-xs text-gray-500">Converted</p>
              <p className="text-xs text-gray-400">{pct(converted, total)}</p>
            </div>
            <div className="bg-amber-50 rounded p-3">
              <p className="font-semibold text-lg text-amber-700">{expired}</p>
              <p className="text-xs text-gray-500">Expired</p>
              <p className="text-xs text-gray-400">{pct(expired, total)}</p>
            </div>
            <div className="bg-red-50 rounded p-3">
              <p className="font-semibold text-lg text-red-700">{unsubscribed}</p>
              <p className="text-xs text-gray-500">Unsubscribed</p>
              <p className="text-xs text-gray-400">{pct(unsubscribed, total)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Conversion by Stage & Source ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle className="text-lg">Conversion by Stage</CardTitle></CardHeader>
          <CardContent>
            {Object.keys(conversionByStage).length === 0 ? (
              <p className="text-sm text-gray-400">No conversions yet</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(conversionByStage).map(([stage, count]) => (
                  <div key={stage} className="flex justify-between text-sm">
                    <span>After Stage {stage} ({STAGE_LABELS[Number(stage)] || stage})</span>
                    <span className="font-semibold">{count as number}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-lg">Conversion by Source</CardTitle></CardHeader>
          <CardContent>
            {Object.keys(conversionBySource).length === 0 ? (
              <p className="text-sm text-gray-400">No conversions yet</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(conversionBySource).map(([source, data]: [string, any]) => (
                  <div key={source} className="flex justify-between text-sm">
                    <span>{source}</span>
                    <span className="font-semibold">
                      {data.converted}/{data.total} ({data.rate || "0"}%)
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Time to Convert ── */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Time to Convert</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-8 text-sm">
            <div>
              <p className="text-gray-500">Average</p>
              <p className="text-xl font-bold">{timeToConvert.averageDays ?? "—"} days</p>
            </div>
            <div>
              <p className="text-gray-500">Median</p>
              <p className="text-xl font-bold">{timeToConvert.medianDays ?? "—"} days</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Referrals ── */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Referrals</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-8 text-sm">
            <div>
              <p className="text-gray-500">Total Referred</p>
              <p className="text-xl font-bold">{referrals.count ?? 0}</p>
            </div>
            <div>
              <p className="text-gray-500">Referred Conversion Rate</p>
              <p className="text-xl font-bold">{referrals.conversionRate ?? "—"}%</p>
            </div>
            <div>
              <p className="text-gray-500">Non-referred Conversion Rate</p>
              <p className="text-xl font-bold">{referrals.nonReferredConversionRate ?? "—"}%</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Email Table ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Captured Emails</CardTitle>
            <div className="flex gap-1">
              {["all", "active", "converted", "expired", "unsubscribed", "bounced"].map((f) => (
                <Button
                  key={f}
                  variant={statusFilter === f ? "default" : "outline"}
                  size="sm"
                  onClick={() => setStatusFilter(f)}
                  className="text-xs capitalize"
                >
                  {f}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="max-h-[400px] overflow-auto">
            <table className="w-full text-sm border-collapse">
              <thead className="sticky top-0 bg-white">
                <tr className="border-b text-left">
                  <th className="py-2 px-2">Email</th>
                  <th className="py-2 px-2">Stage</th>
                  <th className="py-2 px-2">Captured</th>
                  <th className="py-2 px-2">Converted</th>
                  <th className="py-2 px-2">Expired</th>
                  <th className="py-2 px-2">Unsub</th>
                  <th className="py-2 px-2">Bounce</th>
                  <th className="py-2 px-2"></th>
                </tr>
              </thead>
              <tbody>
                {filteredEmails.slice(0, 50).map((e: any) => (
                  <tr key={e.email} className="border-b hover:bg-gray-50">
                    <td className="py-2 px-2 font-mono text-xs">{e.email}</td>
                    <td className="py-2 px-2">{e.reminderStage ?? 0}</td>
                    <td className="py-2 px-2 text-xs">{fmtDate(e.capturedAt)}</td>
                    <td className="py-2 px-2 text-xs">{fmtDate(e.convertedAt)}</td>
                    <td className="py-2 px-2 text-xs">{fmtDate(e.expiredAt)}</td>
                    <td className="py-2 px-2 text-xs">{fmtDate(e.unsubscribedAt)}</td>
                    <td className="py-2 px-2">
                      {e.bounceStatus === "hard" && <Badge variant="destructive">Hard</Badge>}
                      {e.bounceStatus === "soft" && <Badge variant="secondary">Soft</Badge>}
                    </td>
                    <td className="py-2 px-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={sendingTest === e.email}
                        onClick={() => sendTestReminder(e.email)}
                        title="Send Test Reminder"
                      >
                        <Send className="h-3 w-3" />
                      </Button>
                    </td>
                  </tr>
                ))}
                {filteredEmails.length === 0 && (
                  <tr><td colSpan={8} className="py-4 text-center text-gray-400">No emails found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ── Nurture Configuration ── */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Nurture Configuration</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            {paused ? <Pause className="h-4 w-4 text-amber-500" /> : <Play className="h-4 w-4 text-green-500" />}
            <span className="text-sm font-medium">{paused ? "Nurture Paused" : "Nurture Active"}</span>
            <Switch checked={!paused} onCheckedChange={(checked) => setPaused(!checked)} />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {(["stage1", "stage2", "stage3", "stage4"] as const).map((key, i) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">Stage {i + 1} (days)</label>
                <Input
                  type="number"
                  min={1}
                  value={configIntervals[key] ?? ""}
                  onChange={(e) =>
                    setConfigIntervals((prev) => ({ ...prev, [key]: Number(e.target.value) }))
                  }
                  className="w-full"
                />
              </div>
            ))}
          </div>
          <Button onClick={saveConfig} disabled={savingConfig} size="sm">
            {savingConfig ? "Saving…" : "Save Configuration"}
          </Button>
        </CardContent>
      </Card>

      {/* ── A/B Test Results ── */}
      <Card>
        <CardHeader><CardTitle className="text-lg">A/B Test Results</CardTitle></CardHeader>
        <CardContent>
          {!abResults || !abResults.stages || Object.keys(abResults.stages).length === 0 ? (
            <p className="text-sm text-gray-400">No A/B test data available yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-2 px-2">Stage</th>
                    <th className="py-2 px-2">Variant</th>
                    <th className="py-2 px-2">Sent</th>
                    <th className="py-2 px-2">Open Rate</th>
                    <th className="py-2 px-2">Click Rate</th>
                    <th className="py-2 px-2">Conv. Rate</th>
                    <th className="py-2 px-2">Winner</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(abResults.stages).map(([stage, data]: [string, any]) =>
                    ["A", "B"].map((variant) => {
                      const v = data?.[variant] || {};
                      const isWinner = data?.winner === variant;
                      return (
                        <tr key={`${stage}-${variant}`} className="border-b hover:bg-gray-50">
                          {variant === "A" && (
                            <td className="py-2 px-2 font-medium" rowSpan={2}>
                              Stage {stage} ({STAGE_LABELS[Number(stage)] || stage})
                            </td>
                          )}
                          <td className="py-2 px-2">{variant}</td>
                          <td className="py-2 px-2">{v.sent ?? 0}</td>
                          <td className="py-2 px-2">{v.openRate ?? "—"}%</td>
                          <td className="py-2 px-2">{v.clickRate ?? "—"}%</td>
                          <td className="py-2 px-2">{v.conversionRate ?? "—"}%</td>
                          <td className="py-2 px-2">
                            {isWinner && <Badge className="bg-green-100 text-green-800">Winner</Badge>}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminEmailCapture;
