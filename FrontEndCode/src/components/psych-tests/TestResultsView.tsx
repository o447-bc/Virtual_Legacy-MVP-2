import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ArrowLeft, Download, Loader2 } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import type {
  TestDefinition,
  TestResult,
  ScoreEntry,
} from '@/types/psychTests';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a mapping from domain -> facet names using the test definition questions */
function buildDomainFacetMap(
  testDefinition: TestDefinition,
): Map<string, Set<string>> {
  const map = new Map<string, Set<string>>();
  for (const q of testDefinition.questions) {
    const domain = q.scoringKey;
    const facet = q.groupByFacet;
    if (!map.has(domain)) {
      map.set(domain, new Set());
    }
    map.get(domain)!.add(facet);
  }
  return map;
}

function thresholdColor(label: string): string {
  const l = label.toLowerCase();
  if (l === 'high' || l === 'strong') return 'text-green-600';
  if (l === 'average' || l === 'moderate') return 'text-amber-600';
  if (l === 'low' || l === 'weak') return 'text-red-500';
  return 'text-gray-600';
}

function barColor(label: string): string {
  const l = label.toLowerCase();
  if (l === 'high' || l === 'strong') return 'bg-green-500';
  if (l === 'average' || l === 'moderate') return 'bg-amber-500';
  if (l === 'low' || l === 'weak') return 'bg-red-400';
  return 'bg-gray-400';
}

/** Convert a raw score on a 1-5 Likert scale to a 0-100 percentage */
function normalizeScore(raw: number, min = 1, max = 5): number {
  if (max === min) return 50;
  return Math.round(((raw - min) / (max - min)) * 100);
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const ScoreBar: React.FC<{
  entry: ScoreEntry;
  name: string;
  description?: string;
}> = ({ entry, name, description }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const pct = normalizeScore(entry.raw);

  return (
    <div
      className="space-y-1 relative"
      onMouseEnter={() => description && setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div className="flex justify-between items-baseline">
        <span className="text-sm font-medium capitalize cursor-default">
          {name.replace(/_/g, ' ')}
        </span>
        <span className={`text-xs font-semibold ${thresholdColor(entry.label)}`}>
          {entry.label}
        </span>
      </div>
      <div className="relative h-2 w-full rounded-full bg-gray-100 overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all ${barColor(entry.label)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-400">
        <span>{entry.raw.toFixed(1)} / 5.0</span>
        <span>{pct}%</span>
      </div>
      {showTooltip && description && (
        <div className="absolute z-10 left-0 right-0 top-full mt-2 p-3 bg-white border border-gray-200 rounded-lg shadow-lg text-xs text-gray-700 leading-relaxed">
          {description}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface TestResultsViewProps {
  result: TestResult;
  testDefinition: TestDefinition;
  onExport: (format: string) => Promise<void>;
  onBack: () => void;
}

const TestResultsView: React.FC<TestResultsViewProps> = ({
  result,
  testDefinition,
  onExport,
  onBack,
}) => {
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);

  const domainFacetMap = buildDomainFacetMap(testDefinition);

  const handleExport = async (format: string) => {
    setExportingFormat(format);
    try {
      await onExport(format);
    } catch {
      toast({
        title: `${format} export failed`,
        description: 'Please try again.',
        variant: 'destructive',
      });
    } finally {
      setExportingFormat(null);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Back button */}
      <Button
        variant="ghost"
        onClick={onBack}
        className="mb-6 text-gray-600 hover:text-legacy-navy"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back
      </Button>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-legacy-navy">
          {testDefinition.testName} — Results
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Completed {new Date(result.timestamp).toLocaleDateString()}
        </p>
      </div>

      {/* Domain scores with nested facets */}
      {Array.from(domainFacetMap.entries()).map(([domain, facets]) => {
        const domainScore = result.domainScores[domain];
        const facetEntries = Array.from(facets)
          .map((f) => ({ name: f, entry: result.facetScores[f] }))
          .filter((f) => f.entry);

        return (
          <Card key={domain} className="mb-6">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-legacy-navy capitalize">
                {domain.replace(/_/g, ' ')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {domainScore && (
                <ScoreBar
                  entry={domainScore}
                  name={domain}
                  description={testDefinition.domainDescriptions?.[domain]}
                />
              )}

              {facetEntries.length > 0 && (
                <div className="pl-4 border-l-2 border-gray-100 space-y-3 mt-3">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                    Facets
                  </p>
                  {facetEntries.map(({ name, entry }) => (
                    <ScoreBar
                      key={name}
                      entry={entry}
                      name={name}
                      description={testDefinition.domainDescriptions?.[name]}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}

      {/* Narrative text */}
      {result.narrativeText && (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg text-legacy-navy">
              Your Profile
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
              {result.narrativeText}
            </p>
            <p className="text-xs text-gray-400 mt-3">
              {result.narrativeSource === 'bedrock'
                ? 'AI-generated narrative'
                : 'Template-based narrative'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Export buttons */}
      {testDefinition.exportFormats.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {testDefinition.exportFormats.map((format) => (
            <Button
              key={format}
              variant="outline"
              onClick={() => handleExport(format)}
              disabled={exportingFormat !== null}
              className="flex items-center gap-2"
            >
              {exportingFormat === format ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Export {format}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
};

export default TestResultsView;
