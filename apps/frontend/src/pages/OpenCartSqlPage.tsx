import { useEffect, useMemo, useState } from 'react';
import { opencartApi } from '@/api/opencart';
import { useLocalStorage } from '@/hooks/useLocalStorage';
import type {
  OpenCartHistoryDetail,
  OpenCartHistorySummary,
  OpenCartMatchReport,
  OpenCartMatchSettings,
  OpenRouterModel,
} from '@/types/opencart';

const defaultSettings: OpenCartMatchSettings = {
  use_openrouter: false,
  model: 'openai/gpt-4.1-nano',
  fuzzy_threshold: 0.78,
  low_confidence_threshold: 0.86,
  ignore_service_words: true,
};

const emptyReport: OpenCartMatchReport | null = null;

export function OpenCartSqlPage() {
  const [productsText, setProductsText] = useState('');
  const [filesText, setFilesText] = useState('');
  const [imagePrefix, setImagePrefix] = useState('catalog/products/');
  const [apiKey, setApiKey] = useLocalStorage('openrouter_api_key', '');
  const [settings, setSettings] = useState<OpenCartMatchSettings>(defaultSettings);
  const [report, setReport] = useState<OpenCartMatchReport | null>(emptyReport);
  const [history, setHistory] = useState<OpenCartHistorySummary[]>([]);
  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [selectedHistory, setSelectedHistory] = useState<OpenCartHistoryDetail | null>(null);
  const [isWorking, setIsWorking] = useState(false);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [modelLoadError, setModelLoadError] = useState<string | null>(null);

  const canGenerate = useMemo(() => {
    if (!productsText.trim() || !filesText.trim()) return false;
    if (settings.use_openrouter && !apiKey.trim()) return false;
    return true;
  }, [apiKey, filesText, productsText, settings.use_openrouter]);

  useEffect(() => {
    void refreshHistory();
    void refreshModels();
  }, []);

  const currentSql = report?.sql ?? '';

  async function refreshHistory() {
    try {
      const response = await opencartApi.getHistory();
      setHistory(response.items);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load history'));
    }
  }

  async function refreshModels() {
    setIsLoadingModels(true);
    setModelLoadError(null);
    try {
      const response = await opencartApi.getOpenRouterModels();
      setModels(response.items);
    } catch (err) {
      setModelLoadError(err instanceof Error ? err.message : 'Failed to load OpenRouter models');
    } finally {
      setIsLoadingModels(false);
    }
  }

  async function handleGenerate() {
    setIsWorking(true);
    setError(null);
    try {
      const response = await opencartApi.generateImageSql({
        products_text: productsText,
        files_text: filesText,
        image_prefix: imagePrefix,
        settings,
        openrouter_api_key: settings.use_openrouter ? apiKey : undefined,
      });
      setReport(response);
      setSelectedHistory(null);
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to generate SQL'));
    } finally {
      setIsWorking(false);
    }
  }

  async function handleOpenHistory(id: string) {
    setIsWorking(true);
    setError(null);
    try {
      const detail = await opencartApi.getHistoryDetail(id);
      setSelectedHistory(detail);
      setProductsText(detail.products_text);
      setFilesText(detail.files_text);
      setImagePrefix(detail.image_prefix);
      setSettings({ ...defaultSettings, ...detail.settings });
      setReport(detail.result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to open history item'));
    } finally {
      setIsWorking(false);
    }
  }

  return (
    <section className="page-stack opencart-page">
      <div className="page-title-row">
        <div>
          <h1>OpenCart SQL</h1>
          <p className="lede">Assign main product images in OpenCart 3 by generated SQL.</p>
        </div>
        <button
          className="button button--primary"
          type="button"
          disabled={!canGenerate || isWorking}
          onClick={handleGenerate}
        >
          {isWorking ? 'Working...' : 'Generate SQL'}
        </button>
      </div>

      {error && (
        <div className="alert alert--error">
          <div>
            <strong>Error</strong>
            <p>{error.message}</p>
          </div>
          <button className="button button--ghost" type="button" onClick={() => setError(null)}>
            Close
          </button>
        </div>
      )}

      <div className="card form-card">
        <div className="opencart-input-grid">
          <label className="field">
            Products
            <textarea
              value={productsText}
              onChange={(event) => setProductsText(event.target.value)}
              rows={12}
              spellCheck={false}
              placeholder={'12345\tSKU-001\n12346\tSKU-002'}
            />
          </label>
          <label className="field">
            Files
            <textarea
              value={filesText}
              onChange={(event) => setFilesText(event.target.value)}
              rows={12}
              spellCheck={false}
              placeholder={'SKU001.jpg\nsku-002-main.webp'}
            />
          </label>
        </div>

        <div className="opencart-settings-grid">
          <label className="field">
            Image path prefix
            <input value={imagePrefix} onChange={(event) => setImagePrefix(event.target.value)} />
          </label>
          <label className="field">
            OpenRouter API key
            <input
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              autoComplete="off"
            />
          </label>
          <label className="field">
            Model
            {models.length > 0 ? (
              <select
                value={models.some((model) => model.id === settings.model) ? settings.model : '__custom__'}
                onChange={(event) => {
                  if (event.target.value !== '__custom__') {
                    setSettings((current) => ({ ...current, model: event.target.value }));
                  }
                }}
              >
                {!models.some((model) => model.id === settings.model) && (
                  <option value="__custom__">{settings.model}</option>
                )}
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.id})
                  </option>
                ))}
              </select>
            ) : (
              <input
                value={settings.model}
                onChange={(event) => setSettings((current) => ({ ...current, model: event.target.value }))}
              />
            )}
            <small>
              {isLoadingModels
                ? 'Loading OpenRouter models...'
                : modelLoadError
                  ? `Model list unavailable: ${modelLoadError}`
                  : `${models.length} OpenRouter models loaded`}
            </small>
          </label>
        </div>

        <div className="toolbar">
          <label className="field field--inline">
            <input
              type="checkbox"
              checked={settings.use_openrouter}
              onChange={(event) =>
                setSettings((current) => ({ ...current, use_openrouter: event.target.checked }))
              }
            />
            Use OpenRouter
          </label>
          <label className="field field--inline">
            <input
              type="checkbox"
              checked={settings.ignore_service_words}
              onChange={(event) =>
                setSettings((current) => ({ ...current, ignore_service_words: event.target.checked }))
              }
            />
            Ignore service words
          </label>
        </div>
      </div>

      {report && (
        <div className="card result-card opencart-result">
          <div className="opencart-result__header">
            <div className="status-stats">
              <StatusStat label="Matched" value={report.matches.length} tone="success" />
              <StatusStat label="Without file" value={report.unmatched_products.length} tone="warning" />
              <StatusStat label="Unused files" value={report.unused_files.length} tone="info" />
              <StatusStat label="Conflicts" value={report.conflicts.length} tone="danger" />
            </div>
            <button
              className="button button--ghost"
              type="button"
              disabled={!currentSql}
              onClick={() => navigator.clipboard.writeText(currentSql)}
            >
              Copy SQL
            </button>
          </div>

          <pre className="sql-output">{currentSql || 'No SQL generated'}</pre>

          <div className="table-scroll">
            <table className="item-table opencart-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>SKU</th>
                  <th>File</th>
                  <th>Path</th>
                  <th>Method</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {report.matches.map((match) => (
                  <tr key={`${match.product_id}-${match.filename}`}>
                    <td>{match.product_id}</td>
                    <td>{match.sku}</td>
                    <td>{match.filename}</td>
                    <td>{match.image_path}</td>
                    <td>{match.method}</td>
                    <td>{Math.round(match.confidence * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="opencart-report-grid">
            <ReportList
              title="Products without file"
              items={report.unmatched_products.map((product) => `${product.product_id} / ${product.sku}`)}
            />
            <ReportList title="Unused files" items={report.unused_files} />
            <ReportList
              title="Parse errors"
              items={report.parse_errors.map((item) => `Line ${item.line_number}: ${item.message}`)}
            />
            <ReportList
              title="Conflicts"
              items={report.conflicts.map((item) => {
                const target = [item.product_id, item.sku, item.filename].filter(Boolean).join(' / ');
                return target ? `${target}: ${item.message}` : item.message;
              })}
            />
          </div>
        </div>
      )}

      <div className="card form-card">
        <div className="page-title-row">
          <h2>History</h2>
          {selectedHistory && <span className="caption">Opened {selectedHistory.id}</span>}
        </div>
        <div className="history-list">
          {history.length === 0 ? (
            <p className="muted">No history yet.</p>
          ) : (
            history.map((item) => (
              <button
                className="history-item"
                type="button"
                key={item.id}
                onClick={() => handleOpenHistory(item.id)}
              >
                <span>{new Date(item.created_at).toLocaleString()}</span>
                <span>
                  {item.matched_count}/{item.total_products} matched
                </span>
                <span>{item.unused_file_count} unused files</span>
                <span>{item.used_openrouter ? item.model ?? 'LLM' : 'Algorithmic'}</span>
              </button>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

function StatusStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: 'success' | 'warning' | 'danger' | 'info';
}) {
  return (
    <span className={`status-stat status-stat--${tone}`}>
      <span className="status-dot" />
      {label}: {value}
    </span>
  );
}

function ReportList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="opencart-report-list">
      <h3>{title}</h3>
      {items.length === 0 ? (
        <p className="muted">None</p>
      ) : (
        <ul>
          {items.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
