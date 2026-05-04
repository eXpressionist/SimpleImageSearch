import { useState } from 'react';
import type { SearchConfig } from '@/types/api';

interface BatchImportFormProps {
  onSubmit: (lines: string[], name?: string, config?: SearchConfig) => void;
  isLoading?: boolean;
}

export function BatchImportForm({ onSubmit, isLoading }: BatchImportFormProps) {
  const [text, setText] = useState('');
  const [name, setName] = useState('');
  const [prefix, setPrefix] = useState('');
  const [postfix, setPostfix] = useState('');
  const [imagesPerQuery, setImagesPerQuery] = useState(10);

  const lineCount = text.split('\n').filter((line) => line.trim()).length;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const lines = text
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
      .map((line) => [prefix.trim(), line, postfix.trim()].filter(Boolean).join(' '));

    if (lines.length === 0) return;

    onSubmit(lines, name || undefined, { images_per_query: imagesPerQuery });
  };

  return (
    <form className="card form-card" onSubmit={handleSubmit}>
      <h2>Import Products</h2>

      <div className="form-grid">
        <label className="field field--wide">
          <span>Batch Name (optional)</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g., January 2024 Products"
          />
        </label>

        <label className="field">
          <span>Images per query</span>
          <input
            min={1}
            max={200}
            type="number"
            value={imagesPerQuery}
            onChange={(event) =>
              setImagesPerQuery(Math.min(200, Math.max(1, parseInt(event.target.value, 10) || 1)))
            }
          />
          <small>1-200 (Brave limit)</small>
        </label>
      </div>

      <label className="field">
        <span>Prefix (optional)</span>
        <input
          value={prefix}
          onChange={(event) => setPrefix(event.target.value)}
          placeholder="Text to add before each product"
        />
      </label>

      <label className="field">
        <span>Product List</span>
        <textarea
          rows={10}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={'Enter one product per line, e.g.:\nApple iPhone 15 Pro Max 256GB\nSamsung Galaxy S24 Ultra 512GB\nLogitech MX Master 3S'}
          required
        />
        <small>{lineCount} items</small>
      </label>

      <label className="field">
        <span>Postfix (optional)</span>
        <input
          value={postfix}
          onChange={(event) => setPostfix(event.target.value)}
          placeholder="Text to add after each product"
        />
      </label>

      <div className="actions">
        <button className="button button--primary" type="submit" disabled={isLoading || lineCount === 0}>
          {isLoading ? 'Creating...' : 'Start Search'}
        </button>

        <label className="button button--ghost">
          Upload File
          <input
            type="file"
            hidden
            accept=".txt,.csv"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) return;

              const reader = new FileReader();
              reader.onload = (readerEvent) => {
                setText((readerEvent.target?.result as string) || '');
              };
              reader.readAsText(file);
            }}
          />
        </label>
      </div>
    </form>
  );
}
