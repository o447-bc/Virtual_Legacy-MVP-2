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

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const ScoreBar: React.FC<{ entry: ScoreEntry; name: string }> = ({
  entry,
  name,
}) => (
  <div className="space-y-1">
    <div className="flex justify-between items-baseline">
      <span className="text-sm font-medium capitalize">
        {name.replace(/_/g, ' ')}
      </span>
      <span className={`text-xs font-semibold ${thresholdColor(entry.label)}`}>
        {entry.label}
      </span>
    </div>
    <div className="relative h-2 w-full rounded-full bg-gray-100 overflow-hidden">
      <div
        className={`absolute inset-y-0 left-0 rounded-full transition-all ${barColor(entry.label)}`}
        style={{ width: `${Math.min(entry.normalized, 100)}%` }}
      />
    </div>
    <div className="flex justify-between text-xs text-gray-400">
      <span>Raw: {entry.raw}</span>
      <span>{entry.normalized}%</span>
    </div>
  </div>
);

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
              {domainScore && <ScoreBar entry={domainScore} name={domain} />}

              {facetEntries.length > 0 && (
                <div className="pl-4 border-l-2 border-gray-100 space-y-3 mt-3">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                    Facets
                  </p>
                  {facetEntries.map(({ name, entry }) => (
                    <ScoreBar key={name} entry={entry} name={name} />
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
