import { useState } from 'react';
import type { CSSProperties } from 'react';

interface ResilientImageProps {
  sources: string[];
  alt: string;
  className?: string;
  style?: CSSProperties;
  loading?: 'eager' | 'lazy';
}

export function ResilientImage(props: ResilientImageProps) {
  const sources = [...new Set(props.sources.filter(Boolean))];
  return <ImageSources key={sources.join('\n')} {...props} sources={sources} />;
}

function ImageSources({ sources, alt, className, style, loading = 'lazy' }: ResilientImageProps) {
  const [sourceIndex, setSourceIndex] = useState(0);
  if (sourceIndex >= sources.length) {
    return (
      <span className={`image-unavailable ${className || ''}`} style={style} role="img" aria-label={alt}>
        Preview unavailable
      </span>
    );
  }
  return (
    <img
      className={className}
      style={style}
      src={sources[sourceIndex]}
      alt={alt}
      loading={loading}
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setSourceIndex((current) => current + 1)}
    />
  );
}
