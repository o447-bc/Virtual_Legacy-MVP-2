/**
 * Multi-select dropdown for life event keys, grouped by category.
 * Prevents free-text entry — only keys from the canonical registry are selectable.
 */
import { useState, useRef, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { X, ChevronDown } from "lucide-react";
import {
  LIFE_EVENT_REGISTRY,
  LIFE_EVENT_CATEGORIES,
  type LifeEventKeyInfo,
} from "@/constants/lifeEventRegistry";

interface LifeEventTagEditorProps {
  value: string[];
  onChange: (keys: string[]) => void;
  label?: string;
  /** If true, only show instanceable keys */
  instanceableOnly?: boolean;
}

const LifeEventTagEditor: React.FC<LifeEventTagEditorProps> = ({
  value,
  onChange,
  label = "Required Life Events",
  instanceableOnly = false,
}) => {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filteredRegistry = LIFE_EVENT_REGISTRY.filter((entry) => {
    if (instanceableOnly && !entry.isInstanceable) return false;
    if (search) {
      const lower = search.toLowerCase();
      return (
        entry.key.toLowerCase().includes(lower) ||
        entry.label.toLowerCase().includes(lower)
      );
    }
    return true;
  });

  // Group by category
  const grouped: Record<string, LifeEventKeyInfo[]> = {};
  for (const cat of LIFE_EVENT_CATEGORIES) {
    const items = filteredRegistry.filter((e) => e.category === cat);
    if (items.length > 0) grouped[cat] = items;
  }

  const toggle = (key: string) => {
    if (value.includes(key)) {
      onChange(value.filter((k) => k !== key));
    } else {
      onChange([...value, key]);
    }
  };

  const remove = (key: string) => {
    onChange(value.filter((k) => k !== key));
  };

  return (
    <div ref={ref} className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>

      {/* Selected tags */}
      <div
        className="min-h-[38px] border rounded-md px-2 py-1.5 flex flex-wrap gap-1 cursor-pointer bg-white"
        onClick={() => setOpen(!open)}
      >
        {value.length === 0 && (
          <span className="text-gray-400 text-sm">Select life events...</span>
        )}
        {value.map((key) => (
          <Badge
            key={key}
            className="bg-purple-100 text-purple-700 hover:bg-purple-200 gap-1 text-xs"
          >
            {key}
            <X
              className="h-3 w-3 cursor-pointer"
              onClick={(e) => {
                e.stopPropagation();
                remove(key);
              }}
            />
          </Badge>
        ))}
        <ChevronDown className="h-4 w-4 text-gray-400 ml-auto self-center shrink-0" />
      </div>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white border rounded-md shadow-lg max-h-72 overflow-auto">
          <div className="p-2 border-b sticky top-0 bg-white">
            <input
              type="text"
              placeholder="Filter keys..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-sm border rounded px-2 py-1"
              autoFocus
            />
          </div>

          {Object.entries(grouped).map(([category, items]) => (
            <div key={category}>
              <div className="px-3 py-1.5 text-xs font-semibold text-gray-500 bg-gray-50 sticky top-[41px]">
                {category}
              </div>
              {items.map((entry) => {
                const selected = value.includes(entry.key);
                return (
                  <div
                    key={entry.key}
                    className={`px-3 py-1.5 text-sm cursor-pointer flex items-center gap-2 hover:bg-gray-50 ${
                      selected ? "bg-purple-50" : ""
                    }`}
                    onClick={() => toggle(entry.key)}
                  >
                    <input
                      type="checkbox"
                      checked={selected}
                      readOnly
                      className="rounded border-gray-300 text-legacy-purple"
                    />
                    <span className="font-mono text-xs text-gray-500">
                      {entry.key}
                    </span>
                    <span className="text-gray-700 truncate">
                      {entry.label}
                    </span>
                    {entry.isInstanceable && (
                      <Badge className="bg-indigo-100 text-indigo-600 text-[10px] ml-auto">
                        instanceable
                      </Badge>
                    )}
                  </div>
                );
              })}
            </div>
          ))}

          {Object.keys(grouped).length === 0 && (
            <div className="px-3 py-4 text-sm text-gray-400 text-center">
              No matching keys
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LifeEventTagEditor;
